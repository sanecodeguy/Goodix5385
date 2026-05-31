# goodix5385

Fingerprint GUI for the Goodix 5385 (`27c6:5385`) sensor. Enroll, verify,
delete. Toggle sudo auth from the app. Built for Arch / Hyprland.

Fprintd supports this sensor out of the box (driver: `Goodix HTK32`). This
package adds a Qt GUI on top, plus a systemd service that resets the USB
device before fprintd starts (fixes the "fingerprint internal error" after
suspend/resume).

![demo](demo.gif)

## Install (PKGBUILD)

```bash
git clone https://github.com/sanecodeguy/Goodix5385
cd Goodix5385
makepkg -si
```

Or if you want to install it manually:

```bash
sudo pacman -S fprintd python-pyusb python-pyside6
git clone https://github.com/sanecodeguy/Goodix5385
cd Goodix5385
pip install --break-system-packages -e .
sudo cp systemd/goodix-usb-reset.service /etc/systemd/system/
sudo systemctl enable --now goodix-usb-reset.service
sudo cp udev/91-goodix-fingerprint.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

## Usage

```bash
goodix
```

A small always-on-top window appears. From there you can:

| button | what it does |
|---|---|
| + Enroll | tap your finger 8 times. a progress bar fills up. |
| ✓ Verify | match your finger against what you enrolled. |
| ✕ Delete | remove a stored fingerprint. |
| ⌨ Sudo auth | toggle if `sudo` prompts for fingerprint or password. |
| quit | close the app. |

When you enroll or verify, a second overlay window pops up with a
fingerprint animation and status text.

## How it works

The app talks to fprintd over D-Bus using its CLI tools:

- `fprintd-list` — lists enrolled fingers
- `fprintd-enroll` — enrolls a new finger
- `fprintd-verify` — verifies a finger
- `fprintd-delete` — deletes a finger

The systemd service (`goodix-usb-reset`) runs `usb_reset.py` which does a
USB port reset via `pyusb` before fprintd starts. Without this, the sensor
can get stuck in a bad state after suspend and throw "transfer timed out".

The udev rule unbinds the `cdc_acm` kernel driver from the sensor (the
firmware exposes a CDC descriptor that tricks the kernel into claiming it)
and grants user access via `uaccess`.

The sudo auth toggle adds or removes `auth sufficient pam_fprintd.so` from
`/etc/pam.d/sudo` using `pkexec`.

## Files

| path | what |
|---|---|
| `goodix5385/gui/main.py` | bridge between Qt and fprintd CLI tools |
| `goodix5385/gui/fprintd_dbus.py` | subprocess wrappers for fprintd-* |
| `goodix5385/gui/qml/main.qml` | main window layout |
| `goodix5385/gui/qml/FingerprintOverlay.qml` | enroll/verify overlay |
| `goodix5385/scripts/usb_reset.py` | USB reset via pyusb |
| `systemd/goodix-usb-reset.service` | runs usb_reset.py before fprintd |
| `udev/91-goodix-fingerprint.rules` | unbinds cdc_acm, grants access |
| `PKGBUILD` | Arch Linux package build script |

## Building from source

```bash
pip install --break-system-packages .
```

Then `goodix` is on your PATH.

## Dependencies

- `fprintd` — fingerprint daemon (includes the kernel driver)
- `python-pyusb` — USB reset
- `python-pyside6` — Qt GUI
- `polkit` — `pkexec` for the sudo auth toggle

## License

MIT
