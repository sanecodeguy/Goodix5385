#!/usr/bin/env python3
"""CLI fingerprint enrollment using fprintd D-Bus API."""

import dbus
import dbus.mainloop.glib
import sys
from gi.repository import GLib


FPF_DBUS_NAME = "net.reactivated.Fprint"
FPF_DBUS_PATH = "/net/reactivated/Fprint"
FPF_DEVICE_IFACE = "net.reactivated.Fprint.Device"
FPF_MANAGER_IFACE = "net.reactivated.Fprint.Manager"


class FingerprintEnroller:

    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        manager = bus.get_object(FPF_DBUS_NAME, FPF_DBUS_PATH)
        manager_iface = dbus.Interface(manager, FPF_MANAGER_IFACE)
        devices = manager_iface.GetDevices()
        if not devices:
            raise RuntimeError("No fingerprint devices found. Is fprintd running?")
        self.device = bus.get_object(FPF_DBUS_NAME, devices[0])
        self.device_iface = dbus.Interface(self.device, FPF_DEVICE_IFACE)
        self._loop = GLib.MainLoop()
        self._result = None

    def _on_enroll_status(self, result, done):
        if result == "enroll-stage-passed":
            print("  Scan successful — move finger or press again")
        elif result == "enroll-retry-scan":
            print("  Please try again — lift and re-press finger")
        elif result == "enroll-completed":
            print("✓ Enrollment completed successfully!")
            self._result = True
            done()
        elif result == "enroll-data-full":
            print("✓ Enrollment data full")
            self._result = True
            done()
        elif result == "enroll-failed":
            print("✗ Enrollment failed")
            self._result = False
            done()
        elif result == "enroll-unknown":
            print("✗ Unknown enrollment error")
            self._result = False
            done()

    def _on_enroll_error(self, error):
        print(f"✗ Enrollment error: {error}")
        self._result = False
        self._loop.quit()

    def enroll(self, finger="right-index-finger"):
        print(f"\n  Enrolling {finger}")
        print(f"  Place your finger on the sensor...\n")
        self.device_iface.EnrollStart(
            finger,
            reply_handler=lambda: None,
            error_handler=self._on_enroll_error,
        )
        self.device_iface.connect_to_signal(
            "EnrollStatus",
            lambda result, done: self._on_enroll_status(result, done),
        )
        self._loop.run()
        return self._result


def main():
    try:
        enroller = FingerprintEnroller()
        success = enroller.enroll()
        return 0 if success else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
