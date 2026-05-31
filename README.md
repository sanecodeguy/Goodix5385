<div align="center">

# Goodix 5385 Fingerprint

### A native fingerprint GUI for Linux — built for Arch, Hyprland & the Dell XPS 13

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![systemd](https://img.shields.io/badge/systemd-FFD700?style=for-the-badge&logo=linux&logoColor=black)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?style=for-the-badge&logo=arch-linux&logoColor=white)
![Hyprland](https://img.shields.io/badge/Hyprland-58E1FF?style=for-the-badge&logo=wayland&logoColor=black)
![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)

<br>

<img width="1280" height="720" alt="2026-05-3109-10-13-ezgif com-optimize" src="https://github.com/user-attachments/assets/dc3088d6-9627-4571-acdd-1c6f8d5b7f82" />



</div>

---

A Qt-based GUI wrapper around `fprintd` that makes enrolling, verifying, and deleting fingerprints dead simple — no terminal required. Includes a toggle for fingerprint-based `sudo` authentication.

Designed specifically for the **Goodix 5385** sensor (`27c6:5385`), found in:

- **Dell XPS 13 9380** *(primary target)*
- Dell XPS 13 9370
- Other laptops shipping the `27c6:5385` USB fingerprint sensor

> Works reliably on **Arch Linux** with **Hyprland** (Wayland). Should work on other systemd-based distros with minimal tweaks.

---

## Install

**Via AUR (recommended):**

```bash
yay -S goodix5385
```

**Manual build:**

```bash
git clone https://github.com/sanecodeguy/Goodix5385
cd Goodix5385
makepkg -si
```

**Pip (no package manager):**

```bash
pip install --break-system-packages .
```

See the [PKGBUILD](PKGBUILD) for full dependency details.

---

## Usage

```bash
goodix
```

| Button | Action |
|---|---|
| **＋ Enroll** | Tap your finger 8 times to register a new fingerprint |
| **✓ Verify** | Match a finger against enrolled prints |
| **✕ Delete** | Remove an enrolled fingerprint |
| **⌨ Sudo auth** | Toggle fingerprint authentication for `sudo` |
| **Quit** | Close the app |

---

## How it works

The app wraps the standard `fprintd` CLI tools in a PyQt GUI:

- **`fprintd-enroll`** — registers new fingerprints
- **`fprintd-verify`** — matches against stored prints
- **`fprintd-delete`** — removes fingerprints
- **`fprintd-list`** — lists enrolled fingers

**Fixes "fingerprint internal error" after suspend/resume:**  
A systemd service resets the USB device before `fprintd` starts, resolving the common post-resume failure on the XPS 13.

**Driver binding fix:**  
A udev rule unbinds `cdc_acm` from the sensor and grants unprivileged user access to the device.

**Sudo toggle:**  
Edits `/etc/pam.d/sudo` via `pkexec` — no manual PAM configuration needed.

---

## Requirements

- Arch Linux (or any systemd-based distro)
- `fprintd`
- `python-pyqt6` (or PyQt5)
- `polkit` (for the sudo toggle)
- Goodix 5385 sensor (`27c6:5385`)

---

## Credits

- [goodix-fp-dump](https://github.com/goodix-fp-linux-dev/goodix-fp-dump) — USB protocol reverse engineering
- [sigfm](https://github.com/goodix-fp-linux-dev/sigfm) — fingerprint feature matching library
- [goodix53x5-libfprint](https://github.com/AndyHazz/goodix53x5-libfprint) — libfprint driver for the Goodix HTK32 (`27c6:5385`) sensor, Dell XPS 13 7390 / XPS 15 9570

---

## License

[MIT](LICENSE)
