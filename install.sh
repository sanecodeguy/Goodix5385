#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

echo "==> Installing Goodix5385 Fingerprint GUI..."

# 1. Python package (installs `goodix` command)
echo "  -> Installing Python package..."
"${PYTHON}" -m pip install --break-system-packages -e . 2>/dev/null \
  || "${PYTHON}" -m pip install --break-system-packages . 2>/dev/null \
  || echo "  (pip skipped — run: python3 -m goodix5385)"

# 2. udev rule (plugdev group access)
echo "  -> Installing udev rule..."
cp udev/91-goodix-fingerprint.rules /etc/udev/rules.d/
udevadm control --reload-rules

# 3. systemd service (USB reset before fprintd)
echo "  -> Installing systemd service..."
cp systemd/goodix-usb-reset.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable goodix-usb-reset.service
systemctl start goodix-usb-reset.service

echo ""
echo "==> Done. Reboot or run: goodix"
echo "    Then enroll your finger and set up sudo auth in the app."
echo ""
