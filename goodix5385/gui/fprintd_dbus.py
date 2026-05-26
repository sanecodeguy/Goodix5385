"""D-Bus interface to fprintd for fingerprint operations.
Uses dbus-python (GLib main loop) with Qt signals for QML integration.
"""

import dbus
import dbus.mainloop.glib

from PySide6.QtCore import QObject, Signal, Slot
from gi.repository import GLib

FPF_BUS = "net.reactivated.Fprint"
FPF_MANAGER_PATH = "/net/reactivated/Fprint/Manager"
FPF_MANAGER_IFACE = "net.reactivated.Fprint.Manager"
FPF_DEVICE_PATH = "/net/reactivated/Fprint/Device/0"
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
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SystemBus()
        self._device = None
        self._loop = None

    def _find_device(self):
        try:
            manager = self._bus.get_object(
                FPF_BUS, FPF_MANAGER_PATH
            )
            mgr_iface = dbus.Interface(manager, FPF_MANAGER_IFACE)
            devices = mgr_iface.GetDevices()
            if not devices:
                self.deviceFound.emit(False)
                self.error.emit("No fingerprint devices found")
                return False

            path = devices[0]
            self._device = self._bus.get_object(FPF_BUS, path)
            self._device.connect_to_signal(
                "EnrollStatus", self._on_enroll_status
            )
            self._device.connect_to_signal(
                "VerifyStatus", self._on_verify_status
            )
            self.deviceFound.emit(True)
            return True

        except dbus.DBusException as e:
            self.deviceFound.emit(False)
            self.error.emit(f"fprintd error: {e}")
            return False

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
            self.error.emit(f"Unknown: {result}")

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
        iface = dbus.Interface(self._device, FPF_DEVICE_IFACE)
        iface.EnrollStart(finger)

    @Slot(str)
    def start_verify(self, finger=""):
        if not self._find_device():
            return
        iface = dbus.Interface(self._device, FPF_DEVICE_IFACE)
        iface.VerifyStart(finger)

    @Slot()
    def stop_current(self):
        if self._device:
            try:
                iface = dbus.Interface(self._device, FPF_DEVICE_IFACE)
                iface.EnrollStop()
                iface.VerifyStop()
            except Exception:
                pass
