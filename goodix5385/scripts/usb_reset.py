#!/usr/bin/env python3
"""Reset the Goodix 5385 fingerprint sensor from bad USB state.

The sensor sometimes enters a bad state after suspend/resume or failed
communication, causing "transfer timed out" errors. This script performs
a USB port reset to revive the hardware.
"""

import subprocess
import sys
import usb.core
import time

GOODIX_VID = 0x27c6
GOODIX_PID = 0x5385


def find_device():
    dev = usb.core.find(idVendor=GOODIX_VID, idProduct=GOODIX_PID)
    return dev


def reset_device():
    dev = find_device()
    if dev is None:
        print("Goodix5385: device not found")
        return False

    try:
        dev.reset()
        print(f"Goodix5385: USB reset successful (bus {dev.bus} device {dev.address})")
        time.sleep(2)
        return True
    except usb.core.USBError as e:
        print(f"Goodix5385: USB reset failed: {e}", file=sys.stderr)
        return False


def main():
    return 0 if reset_device() else 1


if __name__ == "__main__":
    sys.exit(main())
