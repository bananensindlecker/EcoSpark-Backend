#!/usr/bin/env python3
import subprocess
import time
import signal

class BluetoothManager:
    def __init__(self):
        self.keep_running = True
        signal.signal(signal.SIGINT, self._cleanup)
        signal.signal(signal.SIGTERM, self._cleanup)

    @staticmethod
    def _run_command(command, check=True):
        """Helper method to run shell commands"""
        try:
            subprocess.run(command, shell=True, check=check,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    def _cleanup(self, _signum=None, _frame=None):
        """Cleanup Bluetooth settings on exit"""
        self.keep_running = False
        self._run_command("bluetoothctl -- discoverable off")
        self._run_command("bluetoothctl -- pairable off")

    def reset_bluetooth(self):
        """Reset Bluetooth adapter completely"""
        commands = [
            "sudo systemctl stop bluetooth",
            "sleep 2",
            "sudo rm -f /var/lib/bluetooth/*/settings",
            "sudo systemctl start bluetooth",
            "sleep 2"
        ]
        for cmd in commands:
            if not self._run_command(cmd):
                return False
        return True

    def setup_adapter(self):
        """Configure basic adapter settings"""
        return self._run_command("""bluetoothctl <<EOF
power on
discoverable on
pairable on
EOF""")

    def remove_paired_devices(self):
        """Remove all paired devices"""
        result = subprocess.run(
            "bluetoothctl -- paired-devices | awk '{print $2}'",
            shell=True, capture_output=True, text=True)
        
        devices = result.stdout.splitlines()
        for device in devices:
            if device.strip():
                self._run_command(f"bluetoothctl remove {device}")
        return True

    def configure_io_capability(self):
        """Set IO capability to NoInputNoOutput"""
        return self._run_command("sudo btmgmt --index 0 io-cap 3 >/dev/null 2>&1")

    @staticmethod
    def register_agent():
        """Register NoInputNoOutput agent"""
        try:
            subprocess.run(
                ['expect', '-c', '''
                spawn bluetoothctl
                expect "#"
                send "agent NoInputNoOutput\\r"
                expect {
                    "Agent registered" {}
                    "Failed to register agent object" {exit 1}
                }
                send "default-agent\\r"
                expect "Default agent request successful"
                send "quit\\r"
                expect eof
                '''], 
                check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def keep_discoverable(self, interval=10):
        """Keep Bluetooth discoverable alive"""
        while self.keep_running:
            self._run_command("bluetoothctl -- discoverable on >/dev/null 2>&1")
            time.sleep(interval)

    def full_setup(self):
        """Run the complete setup sequence"""
        steps = [
            self.reset_bluetooth,
            self.setup_adapter,
            self.remove_paired_devices,
            self.configure_io_capability,
            self.register_agent
        ]
        
        for step in steps:
            if not step():
                return False
        return True

def main():
    manager = BluetoothManager()
    if manager.full_setup():
        manager.keep_discoverable()

if __name__ == '__main__':
    main()