import socket
import base64
from pathlib import Path
from convert_data import convert_to_input
from convert_data import clean_base64
from Ecospark_pin import process_sequence
import threading
stop_event = threading.Event()

# Constants for Bluetooth socket
SERVER_ADDRESS = "B8:27:EB:B7:8B:BB"  
PORT = 1             # Standard port for RFCOMM
# Bluetooth constants
AF_BLUETOOTH = 31  # from socket module
SOCK_STREAM = socket.SOCK_STREAM
BT_PROTO_RFCOMM = 3
password = "1234"  # Password for connection verification can be changed

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
    try:
        while True:
            data = client_sock.recv(32768).decode().strip()
            if not data:
                break
            try:
                match int(data[0]):
                    case 0:#  Connecting
                        if data[1:] == password:
                            client_sock.send("Verbindung verifiziert\n".encode())
                            print(f"[>] Received: connection verification")
                        else:
                            client_sock.send("Verbindung fehlgeschlagen\n".encode())
                            print(f"[!] Connection failed: incorrect password")
                            client_sock.close()
                            break
                    case 1:#  Test message
                        client_sock.send("Test erfolgreich \n".encode())
                        print(f"[>] Received: connection test")
                    case 2:#  Send sequence
                        client_sock.send("Abfolge erfolgreich erhalten \n".encode())
                        print(f"[>] Received: sequence ({data})")
                        instructions = convert_to_input(data[1:])
                    case 3:#  audio file
                        client_sock.send("Audio Datei beginnt Transfer\n".encode())
                        print(f"[>] Recieved: Audio file")
                        if ':' in data:
                            _, base64_data = data.split(':', 1)
                            filename, base64_data = base64_data.split(":", 1)
                            if base64_data.strip() == "START":
                                # Receive file in chunks until END
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
                    case 4:  # starting sequence
                        if instructions[0] != "":
                            stop_event.clear()
                            client_sock.send("Startet abfolge\n".encode())
                            # Start the sequence in a new thread
                            seq_thread = threading.Thread(target=process_sequence, args=(instructions,stop_event))
                            seq_thread.start()
                            instructions = [""]  # Reset instructions after processing
                        else:
                            client_sock.send("Keine Abfolge erhalten\n".encode())
                    case 5:#  stop sequence
                        stop_event.set()
                        client_sock.send("Stoppe Abfolge\n".encode())
                        print(f"[>] Received: stop sequence")
            except Exception as e:
                print(f"[!] Error processing data: {e}")
                client_sock.send(f"Fehler bei der Verarbeitung: {str(e)}\n".encode())
                client_sock.close()
                instructions = [""]
                break
    except OSError as e:
        print(f"[!] Error: {e}")
        client_sock.close()
        instructions = [""]
