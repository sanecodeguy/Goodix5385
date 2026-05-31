<div align="center">

# Goodix 5385 Fingerprint
### A native fingerprint GUI for Linux — built for Arch, Hyprland & the Dell XPS 13

<img src="https://img.shields.io/badge/Python-1a3a5c?style=for-the-badge&logo=python&logoColor=85B7EB" />
<img src="https://img.shields.io/badge/Qt-0a3d22?style=for-the-badge&logo=qt&logoColor=5DCAA5" />
<img src="https://img.shields.io/badge/systemd-3d2a00?style=for-the-badge&logo=linux&logoColor=FAC775" />
<img src="https://img.shields.io/badge/Arch_Linux-0d2540?style=for-the-badge&logo=arch-linux&logoColor=378ADD" />
<img src="https://img.shields.io/badge/Hyprland-1a3a3a?style=for-the-badge&logo=wayland&logoColor=1D9E75" />
<img src="https://img.shields.io/badge/License_MIT-1a2e1a?style=for-the-badge&logoColor=97C459" />

<br><br>

<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/f3351c5a-78ce-4a32-a2dc-852682f519d0" /></td>
    <td><img src="https://github.com/user-attachments/assets/b71db3ef-ae8c-4f9e-9766-83751d97b69a" /></td>
    <td><img src="https://github.com/user-attachments/assets/f6a4ed02-eba4-48b6-bc3b-2161f0290e51" /></td>
  </tr>
</table>

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
