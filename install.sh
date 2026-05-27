#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"
PREFIX="${PREFIX:-/usr/local}"
LIBDIR="${LIBDIR:-${PREFIX}/lib/goodix5385}"
BINDIR="${BINDIR:-${PREFIX}/bin}"

echo "==> Installing Goodix5385 Fingerprint Driver & GUI..."

# Install Python package
echo "  -> Installing Python package..."
PIP_OPTS="--break-system-packages"
"${PYTHON}" -m pip install -e . $PIP_OPTS 2>/dev/null || "${PYTHON}" -m pip install . $PIP_OPTS 2>/dev/null || echo "  (skip pip — running directly via python3 -m goodix5385)"

# Install USB reset script
echo "  -> Installing USB reset script..."
mkdir -p "${LIBDIR}/scripts"
cp goodix5385/scripts/usb_reset.py "${LIBDIR}/scripts/"

# Install systemd service
echo "  -> Installing systemd service..."
cp systemd/goodix-usb-reset.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable goodix-usb-reset.service

# Install udev rule
echo "  -> Installing udev rule..."
cp udev/91-goodix-fingerprint.rules /etc/udev/rules.d/
udevadm control --reload-rules

# Create symlink for GUI
echo "  -> Installing GUI launcher..."
cat > "${BINDIR}/goodix5385-gui" << 'LAUNCHER'
#!/usr/bin/env bash
exec python3 -m goodix5385 "$@"
LAUNCHER
chmod +x "${BINDIR}/goodix5385-gui"

echo ""
echo "==> Installation complete!"
echo "    - USB reset service: enabled (resets sensor before fprintd)"
echo "    - GUI: run 'goodix5385-gui' from terminal"
echo ""
echo "    Next steps:"
echo "      1. Reboot or: sudo systemctl start goodix-usb-reset"
echo "      2. Run: goodix5385-gui"
echo "      3. Click system tray icon -> Enroll Fingerprint"
echo ""
