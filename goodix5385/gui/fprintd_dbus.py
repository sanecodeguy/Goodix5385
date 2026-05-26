"""D-Bus interface to fprintd for fingerprint operations."""

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusReply

FPF_SERVICE = "net.reactivated.Fprint"
FPF_MANAGER_PATH = "/net/reactivated/Fprint"
FPF_MANAGER_IFACE = "net.reactivated.Fprint.Manager"
FPF_DEVICE_IFACE = "net.reactivated.Fprint.Device"


class FprintdBackend(QObject):
    enrolled = Signal()
    verifyResult = Signal(bool)
    stagePassed = Signal()
    retryScan = Signal(str)
    error = Signal(str)
    deviceFound = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bus = QDBusConnection.systemBus()
        self._device = None
        self._device_iface = None

    def _find_device(self):
        manager = QDBusInterface(
            FPF_SERVICE, FPF_MANAGER_PATH, FPF_MANAGER_IFACE, self._bus
        )
        if not manager.isValid():
            self.deviceFound.emit(False)
            self.error.emit("fprintd not available")
            return False

        reply = manager.call("GetDevices")
        devices = reply.arguments()[0] if reply.arguments() else []
        if not devices:
            self.deviceFound.emit(False)
            self.error.emit("No fingerprint devices found")
            return False

        self._device = devices[0]
        self._device_iface = QDBusInterface(
            FPF_SERVICE, self._device, FPF_DEVICE_IFACE, self._bus
        )
        if not self._device_iface.isValid():
            self.deviceFound.emit(False)
            self.error.emit("Failed to open device interface")
            return False

        self._device_iface.connect(
            "EnrollStatus", self, self._on_enroll_status
        )
        self._device_iface.connect(
            "VerifyStatus", self, self._on_verify_status
        )
        self.deviceFound.emit(True)
        return True

    def _on_enroll_status(self, result, done):
        if result == "enroll-stage-passed":
            self.stagePassed.emit()
        elif result == "enroll-retry-scan":
            self.retryScan.emit("Lift and re-press your finger")
        elif result in ("enroll-completed", "enroll-data-full"):
            self.enrolled.emit()
        elif result == "enroll-failed":
            self.error.emit("Enrollment failed")
        else:
            self.error.emit(f"Unknown status: {result}")

    def _on_verify_status(self, result, done):
        if result == "verify-match":
            self.verifyResult.emit(True)
        elif result == "verify-no-match":
            self.retryScan.emit("Fingerprint not recognized")
        elif result == "verify-retry-scan":
            self.retryScan.emit("Lift and re-press your finger")
        elif result == "verify-unknown":
            self.error.emit("Verification error")

    @Slot(str)
    def start_enroll(self, finger="right-index-finger"):
        if not self._find_device():
            return
        self._device_iface.call("EnrollStart", finger)

    @Slot()
    def start_verify(self):
        if not self._find_device():
            return
        self._device_iface.call("VerifyStart", "")

    @Slot()
    def stop_current(self):
        if self._device_iface:
            try:
                self._device_iface.call("EnrollStop")
                self._device_iface.call("VerifyStop")
            except Exception:
                pass
