import subprocess
import re

def get_bluetooth_address():
    """
    Returns the Bluetooth MAC address of the first hci device.
    """
    try:
        output = subprocess.check_output("hciconfig", shell=True, text=True)
        match = re.search(r"BD Address: ([0-9A-F:]{17})", output)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[!] Could not get Bluetooth address: {e}")
    return None