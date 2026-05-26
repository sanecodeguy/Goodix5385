# Goodix5385 — Fingerprint Driver & GUI for Linux

Full solution for Goodix 5385 (`27c6:5385`) fingerprint sensor on Linux, featuring a libfprint driver and a Qt/QML GUI for enrollment.

## Features

- **libfprint driver** — GTLS protocol, SIGFM matching, 108×88 capacitive sensor
- **USB reset service** — Fixes "transfer timed out" bad-state issue automatically at boot
- **Qt/QML GUI** — Floating overlay like Windows fingerprint enrollment
- **PAM integration** — Use fingerprint for `sudo` and system auth

## Quick Start

### Prerequisites

```bash
# Install dependencies
sudo pacman -S python-pyside6 python-dbus pyusb
# Or on Debian: sudo apt install python3-pyside6 python3-dbus python3-usb
```

### Install

```bash
# Install the Python package and system integration
sudo ./install.sh
```

### Use

```bash
# Launch the GUI (system tray app)
python3 -m goodix5385.gui

# Or enroll via CLI
python3 -m goodix5385.scripts.enroll
```

## GUI (Qt/QML)

The GUI runs as a system tray application. Click the tray icon to:
- **Enroll Fingerprint** — Select finger → guided 8-scan enrollment with visual feedback
- **Verify Fingerprint** — Quick match test

The floating overlay shows fingerprint animation, scan progress dots, and clear status messages.

## USB Reset Fix

The sensor sometimes enters a bad state after suspend/resume. The included systemd service (`goodix-usb-reset.service`) resets the USB device before fprintd starts.

## PAM Setup

```bash
# Add to /etc/pam.d/sudo:
# auth       sufficient   pam_fprintd.so
# auth       include      system-auth
```

## Project Structure

```
goodix5385/
├── drivers/goodix53x5/    # libfprint C driver source
├── sigfm/                 # SIGFM fingerprint matcher (C++)
├── gui/                   # Qt/QML Python GUI
│   ├── main.py           # Application entry point
│   ├── fprintd_dbus.py   # D-Bus fprintd backend
│   └── qml/              # QML UI components
├── scripts/               # USB reset, CLI enrollment
├── udev/                  # udev rules
├── systemd/               # systemd services
└── install.sh             # Automated installer
```

## Credits

- libfprint driver: [AndyHazz/goodix53x5-libfprint](https://github.com/AndyHazz/goodix53x5-libfprint)
- Original Python driver: [sanecodeguy/Goodix5385](https://github.com/sanecodeguy/Goodix5385)
- SIGFM: [goodix-fp-linux-dev/sigfm](https://github.com/goodix-fp-linux-dev/sigfm)
