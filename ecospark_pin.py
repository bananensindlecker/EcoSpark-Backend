import time
import RPi.GPIO as GPIO
from pathlib import Path
import pygame

class AudioController:

    def __init__(self):
        self.played_files = set()
        self.current_file = None
        self.current_volume = 1.0  # pygame volume: 0.0 - 1.0
        self._initialize_player()

    @staticmethod
    def _initialize_player():
        """Initialisiert pygame.mixer"""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init()
            print("[*] pygame.mixer initialized")
        except Exception as e:
            print(f"[?] Failed to initialize pygame.mixer: {e}")
            raise

    def play(self, file_path, volume=100):
        """Spiele Audio mit minimaler Verzoegerung ab (non-blocking, effizient)"""
        if not file_path.exists():
            print(f"[?] Audio-Datei nicht gefunden: {file_path}")
            return False

        try:
            self.played_files.add(file_path)
            # Lade und spiele die Datei ab (WAV/OGG empfohlen)
            sound = pygame.mixer.Sound(str(file_path))
            sound.set_volume(max(0.0, min(1.0, volume / 100)))
            sound.play()
            print(f"[!] Playing audio file: {file_path.name}")
            return True
        except Exception as e:
            print(f"[?] Playback failed: {e}")
            return False

    def cleanup(self):
        """Bereinigt Ressourcen"""
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except Exception as e:
            print(f"[?] pygame.mixer cleanup failed: {e}")

        # Entfernt abgespielte Dateien
        for mp3 in self.played_files:
            try:
                if mp3.exists():
                    mp3.unlink()
            except Exception as e:
                print(f"[?] Loeschen fehlgeschlagen: {mp3} - {e}")
        self.played_files.clear()

def process_instruction_list(instructions:list[str], audio_controller:AudioController,stop_event):
    stopped = False
    while not stopped:
        if stop_event.is_set():
            print("[*] Sequence cancelled by user.")
            break
        # GPIO Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Constants
        instructions_dir = Path.home() / 'Desktop' / 'Instructions'
        instructions_dir.mkdir(exist_ok=True)

        try:
            events = []
            active_pins = set()

            for instruction in instructions:
                if instruction.lower() == "stop":
                    stop_time = events[-1][0] if events else 0
                    events.append((stop_time, 'STOP', None))
                    break

                if not instruction.startswith('T'):
                    continue

                try:
                    parts = instruction[1:].split()
                    time_ms = int(parts[0])
                    mp3_file = None
                    volume = 100
                    skip_next = False

                    for idx, item in enumerate(parts[1:]):
                        if skip_next:
                            skip_next = False
                            continue
                        # Only accept .wav files
                        if item.lower().endswith('.wav'):
                            mp3_file = instructions_dir / item.strip()
                            # Check if the next part is a volume number
                            if idx + 2 <= len(parts) - 1:
                                next_item = parts[idx + 2]
                                try:
                                    vol_candidate = int(next_item)
                                    if 0 <= vol_candidate <= 100:
                                        volume = vol_candidate
                                        skip_next = True
                                except Exception:
                                    pass
                            print(f"[*]Looking for audio file: '{item.strip()}' at {mp3_file}")
                        elif item.startswith('+P'):
                            try:
                                pin = int(item[2:])
                                events.append((time_ms, 'PIN_ON', pin))
                            except Exception:
                                continue
                        elif item.startswith('-P'):
                            try:
                                pin = int(item[2:])
                                events.append((time_ms, 'PIN_OFF', pin))
                            except Exception:
                                continue

                    # Audio event
                    if mp3_file and mp3_file.exists():
                        events.append((time_ms, 'AUDIO', (mp3_file, volume)))

                except Exception as e:
                    print(f"[?] Error parsing instruction: {instruction} - {e}")

            # If no STOP event was found, add one at the last event time
            if not any(ev[1] == 'STOP' for ev in events):
                last_time = events[-1][0] if events else 0
                events.append((last_time, 'STOP', None))

            # Execute events (rest of your existing code...)
            events.sort()
            start_time = time.time() * 1000
            event_idx = 0

            print("\n[*] Starting event processing")
            print("[!] Events to process:")
            for idx, (time_ms, event_type, value) in enumerate(events):
                print(f"[{idx}] {time_ms}ms - {event_type} - {value}")
            print("\n")

            stopped = False
            while not stopped:
                if stop_event.is_set():
                    print("[*] Sequence cancelled by user.")
                    break
                current_ms = time.time() * 1000 - start_time

                # Track previous pin states
                prev_states = {pin: GPIO.input(pin) for pin in active_pins}

                # Process all events that should happen at this time
                while event_idx < len(events) and events[event_idx][0] <= current_ms:
                    time_ms, event_type, value = events[event_idx]

                    # Handle event
                    if event_type == 'PIN_ON':
                        GPIO.setup(value, GPIO.OUT)
                        GPIO.output(value, GPIO.HIGH)
                        if prev_states.get(value, GPIO.LOW) == GPIO.LOW:
                            print(f"[+] Pin {value} HIGH")
                    elif event_type == 'PIN_OFF':
                        GPIO.setup(value, GPIO.OUT)
                        GPIO.output(value, GPIO.LOW)
                        if prev_states.get(value, GPIO.HIGH) == GPIO.HIGH:
                            print(f"[-] Pin {value} LOW")
                    elif event_type == 'AUDIO':
                        if not audio_controller.play(*value):
                            print(f"[?] Failed to play audio file: {value[0].name}")
                            continue
                        print(f"[!] Audio started: {value[0].name}")
                    elif event_type == 'STOP':
                        print("[*] STOP event reached. Ending processing.")
                        stopped = True

                        # Wait for all audio playbacks to finish before cleanup
                        while pygame.mixer.get_busy():
                            time.sleep(0.1)

                        # Cleanup: Delete all played audio files
                        for value in [ev[2] for ev in events if ev[1] == 'AUDIO']:
                            audio_file = value[0]
                            try:
                                if audio_file.exists():
                                    audio_file.unlink()
                                    print(f"[*] Deleted audio file: {audio_file.name}")
                                else:
                                    print(f"[?] Audio file not found for deletion: {audio_file.name}")
                            except Exception as e:
                                print(f"[?] Failed to delete audio file {audio_file.name}: {e}")
                    event_idx += 1


                if not stopped:
                    time.sleep(0.01) 

            # Cleanup: Pins deaktivieren
            for pin in active_pins:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

            time.sleep(0.1)

            return True

        except Exception as e:
            print(f"[?] Error processing:{e}")
            return False
    return False


def process_sequence(instructions:list[str],stop_event):
    print("[*] Starting GPIO+Audio Controller")

    audio_controller = AudioController()
    
    try:
        print("[*] Processing ...")
        if process_instruction_list(instructions, audio_controller,stop_event):
            print("[!] Process completed")
        else:
            print("[?] Failed to process")

        time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        audio_controller.cleanup()
        GPIO.cleanup()
        print("\n[*] Controller stopped.")

