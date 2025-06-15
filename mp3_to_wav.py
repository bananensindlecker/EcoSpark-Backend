#!/usr/bin/env python3
import subprocess
from pathlib import Path
import time

class AudioConverter:
    def __init__(self, instructions_dir=None):
        self.instructions_dir = instructions_dir or Path.home() / 'Desktop' / 'Instructions'
        self.ensure_directory_exists()
        self.known_files = set()

    def ensure_directory_exists(self):
        """Create directory if it doesn't exist"""
        self.instructions_dir.mkdir(exist_ok=True)

    @staticmethod
    def convert_mp3_to_wav(mp3_path):
        """Convert single MP3 to WAV, delete original if successful"""
        try:
            wav_path = mp3_path.with_suffix('.wav')
            subprocess.run([
                'ffmpeg',
                '-i', str(mp3_path),
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '44100',
                '-hide_banner',
                '-loglevel', 'error',
                '-y',
                str(wav_path)
            ], check=True, timeout=2)
            
            if wav_path.exists():
                mp3_path.unlink()
                return True
        except (subprocess.SubprocessError, OSError):
            return False

    def process_new_files(self):
        """Convert any new MP3 files found in directory"""
        current_files = set(self.instructions_dir.glob('*.mp3'))
        new_files = current_files - self.known_files
        for mp3 in new_files:
            success = self.convert_mp3_to_wav(mp3)
            if not success:
                return False
        self.known_files = current_files
        return True


    def monitor(self, interval=0.5, max_iterations=None):
        """Monitor directory for new files with optional exit condition
        
        Args:
            interval: Seconds between checks
            max_iterations: Optional limit to number of checks
        """
        iterations = 0
        while True:
            if max_iterations and iterations >= max_iterations:
                break
                
            self.process_new_files()
            time.sleep(interval)
            iterations += 1

def convert_mp3_to_wav():
    converter = AudioConverter()
      # Process existing files first
    # converter.monitor()  # Start monitoring
    if converter.process_new_files():
        return True
    return False


if __name__ == '__main__':
    convert_mp3_to_wav()