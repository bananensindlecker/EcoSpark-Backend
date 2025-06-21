import socket
import base64
from pathlib import Path
import hashlib
import threading
from bluetooth_auto_accept import auto_accept_bluetooth
from convert_data import convert_to_input
from convert_data import clean_base64
from ecospark_pin import process_sequence
from find_bluetooth import get_bluetooth_address

"""
Bluetooth server for receiving commands to control GPIO pins and audio playback on a Raspberry Pi.
"""


#  Initializing the stop event for sequence control
stop_event = threading.Event()

#  Constants for Bluetooth socket
SERVER_ADDRESS = get_bluetooth_address()#  Automatically get the Bluetooth address
if not SERVER_ADDRESS:
    raise RuntimeError("Could not determine Bluetooth address automatically.")
PORT = 1             #  Port for RFCOMM

#  Bluetooth constants
AF_BLUETOOTH = 31  #  From socket module
SOCK_STREAM = socket.SOCK_STREAM
BT_PROTO_RFCOMM = 3

#  Start Bluetooth discoverability in a separate thread
make_discoverable = threading.Thread(target=auto_accept_bluetooth())
make_discoverable.start()

#  Password for connection verification can be changed
password = "15Punkte"  
print(f"[*] Password is: {password}")

#  Hashing password for secure conperasion
hasher = hashlib.sha3_256()
hasher.update(password.encode('utf8'))
hashed_password = hasher.hexdigest()



#  Loops in case of errors or disconnects
while True:
    # Creating the Bluetooth socket
    server_sock = socket.socket(AF_BLUETOOTH, SOCK_STREAM, BT_PROTO_RFCOMM)
    server_sock.bind((SERVER_ADDRESS, PORT))
    server_sock.listen(1)
    print(f"[*] Listening for RFCOMM connections on channel {PORT}...")
    client_sock, client_info = server_sock.accept()
    print(f"[+] Accepted connection from {client_info}")
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
    instructions: list[str] = [""]
    logged_in:bool = False
    try:
        #  Loops to handle incoming data
        while True:
            #  Receiving and decoding data
            data = client_sock.recv(32768).decode().strip()
            if not data:
                break
            try:
                match int(data[0]):
                    case 0:#  Connecting and checking password
                        print(f"[!] received password hash: {data[1:]}")
                        if data[1:] == hashed_password:
                            client_sock.send("Verbindung verifiziert\n".encode())
                            print(f"[>] Received: connection verification")
                            logged_in = True
                        else:
                            client_sock.send("Verbindung fehlgeschlagen\n".encode())
                            print(f"[!] Connection failed: incorrect password")
                            client_sock.close()
                            break
                    case 1:#  Test message for debug perposes
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        client_sock.send("Test erfolgreich \n".encode())
                        print(f"[>] Received: connection test")
                    case 2:#  Send a sequence
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        client_sock.send("Abfolge erfolgreich erhalten \n".encode())
                        print(f"[>] Received: sequence ({data})")
                        instructions = convert_to_input(data[1:])
                    case 3:#  Send a audio file
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        client_sock.send("Audio Datei beginnt Transfer\n".encode())
                        print(f"[>] Received: Audio file")
                        if ':' in data:
                            _, base64_data = data.split(':', 1)
                            filename, base64_data = base64_data.split(":", 1)
                            if base64_data.strip() == "START":
                                # Receive a file in chunks until END
                                file_chunks = []
                                while True:
                                    chunk = client_sock.recv(32768).decode()
                                    if "END" in chunk:
                                        file_chunks.append(chunk.replace("END", ""))
                                        break
                                    file_chunks.append(chunk)
                                full_base64_data = ''.join(file_chunks).rstrip('\n')
                                # Clean and pad base64 before decoding
                                full_base64_data = clean_base64(full_base64_data)
                                with open(f"{Path.home()}/Desktop/Instructions/{filename}", "wb") as new_file:
                                    new_file.write(base64.b64decode(full_base64_data))
                                print(f"[*] Audio file saved as {filename}")
                                client_sock.send(f"Audio Datei gespeichet als {filename}\n".encode())
                    case 4:#  Starting sequence (sequence must be send first)
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        if instructions[0] != "":
                            stop_event.clear()
                            print(f"[>] Starting a sequence")
                            client_sock.send("Startet abfolge\n".encode())
                            # Start the sequence in a new thread
                            seq_thread = threading.Thread(target=process_sequence, args=(instructions,stop_event))
                            seq_thread.start()
                            instructions = [""]  # Reset instructions after processing
                        else:
                            client_sock.send("Keine Abfolge erhalten\n".encode())
                    case 5:#  stops running sequence
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        stop_event.set()
                        client_sock.send("Stoppe Abfolge\n".encode())
                        print(f"[>] Received: stop sequence")
                    case 6:#  Shutting down the raspberry pi
                        if not logged_in:
                            client_sock.send("Nicht angemeldet \n".encode())
                            print(f"[!] Tried sending without being logged in")
                            continue
                        client_sock.send("Fahre Raspberry Pi herunter\n".encode())
                        print(f"[>] Received: shutdown command") 
                        client_sock.close()
                        server_sock.close()
                        try:
                            import os
                            #  Gracefully close sockets and send shutdown command to OS
                            os.system("sudo shutdown now")
                        except Exception as e:
                            print(f"[!] Error shutting down: {e}")
                            client_sock.send(f"Fehler beim Herunterfahren: {str(e)}\n".encode())
            except Exception as e:#  Handling errors in data processing
                print(f"[!] Error processing data: {e}")
                client_sock.send(f"Fehler bei der Verarbeitung: {str(e)}\n".encode())
                instructions = [""]
                break
    except OSError as e:#  Handling socket errors and connection issues
        print(f"[!] Error: {e}")
        client_sock.close()
        logged_in = False
        instructions = [""]

