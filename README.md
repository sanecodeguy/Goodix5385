# Goodix5385

Goodix 5385 fingerprint sensor driver for Dell XPS 13 9380 (Arch Linux).

Reverse-engineered from [goodix-fp-dump](https://github.com/goodix-fp-linux-dev/goodix-fp-dump)
with SIGFM fingerprint matching.

## Architecture

- **Python driver** — USB communication, GTLS handshake, image capture
- **C++ SIGFM** — SIFT-based fingerprint matching (enrollment + authentication)

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Build SIGFM
```bash
make sigfm
```
Requires OpenCV 4 with `opencv_contrib` (for SIFT).

### Capture a fingerprint
```bash
python -m goodix5385.cli capture -o test.pgm
```

### Enroll fingerprints (multi-angle)
```bash
python scripts/enroll.py --outdir enrolled --count 6
```

### Authenticate
```bash
python scripts/authenticate.py --templates enrolled
```

## Hardware

| Attribute | Value |
|-----------|-------|
| Vendor  | 0x27c6 |
| Product | 0x5385 |
| Sensor  | GF5288_HTSEC |
| Resolution | 108 x 88 |
| Firmware | GF5288_HTSEC_APP_10011 |

## PAM Integration

```bash
# After enrollment, add to /etc/pam.d/sudo:
auth sufficient pam_exec.so /usr/local/bin/pam_goodix5385.py
```

## Project Structure

```
Goodix5385/
├── goodix5385/        # Python driver package
│   ├── protocol.py    # USB communication
│   ├── wrapless.py    # Goodix wrapless protocol + GTLS
│   ├── driver.py      # 5385 sensor driver
│   ├── tool.py        # Image decode/PGM
│   ├── preprocessor.py# Image preprocessing
│   └── config.py      # Constants
├── sigfm/             # C++ fingerprint matcher
│   ├── compute.cpp    # Enrollment (feature extraction)
│   ├── match.cpp      # Authentication (matching)
│   └── structs.hpp    # Shared types
├── scripts/           # CLI tools
├── pam/               # PAM module
├── udev/              # udev rules
└── systemd/           # systemd service
```
