# goodix5385

Fingerprint GUI for the Goodix 5385 (`27c6:5385`) sensor. Enroll, verify,
delete. Toggle sudo auth from the app. Built for Arch / Hyprland.

![demo](demo.gif)

## Install

```bash
yay -S goodix5385
```

Or clone, `makepkg -si`, or `pip install --break-system-packages .` (see
[PKGBUILD](PKGBUILD) for details).

## Usage

```
goodix
```

| button | what it does |
|---|---|
| + Enroll | tap your finger 8 times |
| ✓ Verify | match against an enrolled finger |
| ✕ Delete | remove a fingerprint |
| ⌨ Sudo auth | toggle fingerprint for `sudo` |
| quit | close |

## How it works

The app wraps fprintd CLI tools (`fprintd-list`, `fprintd-enroll`,
`fprintd-verify`, `fprintd-delete`) in a Qt GUI. A systemd service resets
the USB device before fprintd starts (fixes "fingerprint internal error"
after resume). A udev rule unbinds `cdc_acm` from the sensor and grants
user access. The sudo toggle edits `/etc/pam.d/sudo` via `pkexec`.

## Credits

- [goodix-fp-dump](https://github.com/goodix-fp-linux-dev/goodix-fp-dump) —
  protocol reverse engineering
- [sigfm](https://github.com/goodix-fp-linux-dev/sigfm) — feature matching
  library

## License

MIT
