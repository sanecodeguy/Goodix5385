#!/usr/bin/env python3
"""Goodix5385 Fingerprint Enrollment GUI — Qt/QML frontend for fprintd."""

import os
import shutil
import subprocess
import sys
import time

from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from .fprintd_dbus import FprintdBackend

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
SYSTEMD_SERVICE = "goodix-usb-reset.service"
SYSTEMD_SERVICE_PATH = "/etc/systemd/system/" + SYSTEMD_SERVICE
PAM_SUDO = "/etc/pam.d/sudo"


class FprintBridge(QObject):
    def __init__(self, backend: FprintdBackend, engine: QQmlApplicationEngine, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._engine = engine
        self._root = None
        self._cached_fingers = []
        self._sudo_enabled = _sudo_auth_status()

        backend.enrolled.connect(self._on_enrolled)
        backend.stagePassed.connect(self._on_stage_passed)
        backend.retryScan.connect(self._on_retry)
        backend.error.connect(self._on_error)
        backend.verifyResult.connect(self._on_verify_result)
        backend.deviceFound.connect(self._on_device_found)
        backend.enrolledFingersChanged.connect(self._on_enrolled_fingers)

    def _get_root(self):
        if self._root is None:
            objs = self._engine.rootObjects()
            if objs:
                self._root = objs[0]
        return self._root

    def _get_overlay(self):
        root = self._get_root()
        if root:
            return root.findChild(QObject, "overlay")
        return None

    def _on_enrolled(self):
        overlay = self._get_overlay()
        if overlay:
            overlay.setProperty("success", True)
            overlay.setProperty("status", "Enrollment complete!")
            overlay.setProperty("scanCount", 8)
            overlay.setProperty("fingerName", "")
        # Refresh enrolled fingers list for delete/verify dialogs
        self._backend.find_device()

    def _on_stage_passed(self):
        overlay = self._get_overlay()
        if overlay:
            cnt = overlay.property("scanCount") + 1
            overlay.setProperty("scanCount", cnt)
            overlay.setProperty("status", "Fingerprint captured — lift and press again")

    def _on_retry(self, msg: str):
        overlay = self._get_overlay()
        if overlay:
            is_enrolling = overlay.property("isEnrolling")
            if is_enrolling:
                overlay.setProperty("retryMode", False)
            else:
                overlay.setProperty("retryMode", True)
                overlay.setProperty("scanCount", 0)
            overlay.setProperty("status", msg)

    def _on_device_found(self, found: bool):
        root = self._get_root()
        if root:
            root.setProperty("deviceAvailable", found)
            root.setProperty("statusMessage", "Device ready" if found else "No fingerprint device found")

    def _on_error(self, msg: str):
        overlay = self._get_overlay()
        if overlay:
            overlay.setProperty("status", f"Error: {msg}")

    def _on_enrolled_fingers(self, fingers: list):
        self._cached_fingers = fingers
        root = self._get_root()
        if root:
            dlg = root.findChild(QObject, "fingerDialog")
            if dlg:
                dlg.setProperty("enrolledFingers", fingers)

    @Slot(str)
    def on_verify(self, finger=""):
        self._backend.start_verify(finger)

    def _on_verify_result(self, matched: bool):
        overlay = self._get_overlay()
        if overlay:
            if matched:
                overlay.setProperty("success", True)
                overlay.setProperty("status", "Verified!")
                overlay.setProperty("retryMode", False)
                overlay.setProperty("fingerName", "")
            else:
                overlay.setProperty("retryMode", True)
                overlay.setProperty("status", "Not recognized — try again")
                overlay.setProperty("scanCount", 0)

    @Slot(str)
    def on_enroll(self, finger: str):
        self._backend.start_enroll(finger)

    @Slot(str)
    def on_delete(self, finger: str):
        self._backend.delete_finger(finger)

    @Slot()
    def on_stop(self):
        self._backend.stop_current()

    # ── Sudo auth toggle ─────────────────────────────────────────────────────

    @Slot(result=bool)
    def sudoAuthEnabled(self):
        return self._sudo_enabled

    @Slot(bool, result=bool)
    def setSudoAuth(self, enabled: bool):
        self._sudo_enabled = _sudo_auth_set(enabled)
        root = self._get_root()
        if root:
            root.setProperty("sudoAuthEnabled", self._sudo_enabled)
        if self._sudo_enabled != enabled:
            self._backend.error.emit(
                "Failed to update sudo auth — check that pkexec/sudo works")
        return self._sudo_enabled


def _ensure_systemd_service():
    """Install and enable the USB-reset systemd service if not already active."""
    if not shutil.which("systemctl"):
        return
    try:
        r = subprocess.run(["systemctl", "is-enabled", SYSTEMD_SERVICE], capture_output=True, text=True)
        if r.returncode != 0 or "enabled" not in r.stdout:
            src = os.path.join(os.path.dirname(__file__), "..", "..", "systemd", SYSTEMD_SERVICE)
            if os.path.exists(src):
                subprocess.run(["sudo", "cp", src, SYSTEMD_SERVICE_PATH], check=True)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", SYSTEMD_SERVICE], check=True)
                print("  -> USB-reset service installed & enabled")
            else:
                print("  WARN: systemd service file not found at", src)
    except Exception as e:
        print(f"  WARN: could not install systemd service: {e}")


def _reset_usb_and_fprintd():
    """Reset the fingerprint sensor USB device and restart fprintd."""
    try:
        subprocess.run([sys.executable, "-m", "goodix5385.scripts.usb_reset"],
                       capture_output=True, timeout=10)
    except Exception as e:
        print(f"  WARN: USB reset failed: {e}")

    # Restart fprintd so it re-claims the freshly-reset device
    try:
        subprocess.run(["sudo", "systemctl", "restart", "fprintd.service"],
                       capture_output=True, timeout=15)
    except Exception as e:
        print(f"  WARN: fprintd restart failed: {e}")


def _sudo_auth_status():
    """Check whether fingerprint auth for sudo is enabled."""
    if not os.path.exists(PAM_SUDO):
        return False
    try:
        with open(PAM_SUDO) as f:
            return "pam_fprintd.so" in f.read()
    except OSError:
        return False


def _sudo_auth_set(enable: bool) -> bool:
    """Add or remove the pam_fprintd line from /etc/pam.d/sudo."""
    if not os.path.exists(PAM_SUDO):
        return False
    try:
        with open(PAM_SUDO) as f:
            lines = f.readlines()
    except OSError:
        return False

    has_line = any("pam_fprintd.so" in l for l in lines)

    if enable and not has_line:
        # Insert before the first `auth required` or `auth sufficient` line
        insert_at = 0
        for i, l in enumerate(lines):
            if l.strip().startswith("auth") and ("required" in l or "sufficient" in l or "include" in l):
                insert_at = i
                break
        lines.insert(insert_at, "auth sufficient pam_fprintd.so\n")
    elif not enable and has_line:
        lines = [l for l in lines if "pam_fprintd.so" not in l]
    else:
        return True  # already in desired state

    text = "".join(lines)
    try:
        # Use pkexec (graphical polkit) so the user gets a password prompt
        tee_cmd = shutil.which("pkexec") or shutil.which("sudo") or ""
        if not tee_cmd:
            return False
        p = subprocess.Popen([tee_cmd, "tee", PAM_SUDO], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.communicate(text.encode())
        if p.returncode != 0:
            return False
        # Return actual state (same as enable on success, opposite on failure)
        return _sudo_auth_status()
    except Exception:
        return False


def _ensure_deps():
    """Install missing system dependencies (fprintd, libfprint-goodix53x5)."""
    missing = []
    if not shutil.which("fprintd-list"):
        missing.append("fprintd")
    try:
        r = subprocess.run(["pacman", "-Qi", "libfprint-goodix53x5"],
                           capture_output=True, text=True)
        if r.returncode != 0 or "Name" not in r.stdout:
            missing.append("libfprint-goodix53x5")
    except FileNotFoundError:
        missing.append("libfprint-goodix53x5")

    if not missing:
        return

    print(f"  -> Missing deps: {', '.join(missing)} — installing...")
    pkexec = shutil.which("pkexec") or shutil.which("sudo") or ""
    if not pkexec:
        print("  ERROR: need pkexec or sudo to install deps")
        return

    for pkg in missing:
        if pkg == "fprintd":
            subprocess.run([pkexec, "pacman", "-S", "--noconfirm", "--needed", "fprintd"],
                           capture_output=True)
        elif pkg == "libfprint-goodix53x5":
            subprocess.run([pkexec, "sh", "-c",
                           f"yay -S --noconfirm --needed libfprint-goodix53x5 2>&1 || "
                           f"pacman -S --noconfirm --needed libfprint-goodix53x5 2>&1 || true"],
                           capture_output=True)
    print("  -> Deps installed")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Goodix5385 Fingerprint")
    app.setQuitOnLastWindowClosed(True)

    backend = FprintdBackend()
    engine = QQmlApplicationEngine()

    bridge = FprintBridge(backend, engine)
    engine.rootContext().setContextProperty("fprintBridge", bridge)

    qml_path = QUrl.fromLocalFile(os.path.join(QML_DIR, "main.qml"))
    engine.load(qml_path)

    if not engine.rootObjects():
        print("Failed to load QML UI", file=sys.stderr)
        return 1

    # ── Startup tasks (best-effort) ──────────────────────────────────────────
    _ensure_deps()
    _ensure_systemd_service()
    _reset_usb_and_fprintd()
    time.sleep(0.5)

    # Sync initial PAM sudo-auth state to QML
    root = bridge._get_root()
    if root:
        root.setProperty("sudoAuthEnabled", _sudo_auth_status())

    backend.find_device()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
