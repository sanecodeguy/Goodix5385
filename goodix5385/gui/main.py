#!/usr/bin/env python3
"""Goodix5385 Fingerprint Enrollment GUI — Qt/QML frontend for fprintd."""

import os
import sys

from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from .fprintd_dbus import FprintdBackend

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")


class FprintBridge(QObject):
    def __init__(self, backend: FprintdBackend, engine: QQmlApplicationEngine, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._engine = engine
        self._root = None
        self._cached_fingers = []

        backend.enrolled.connect(self._on_enrolled)
        backend.stagePassed.connect(self._on_stage_passed)
        backend.retryScan.connect(self._on_retry)
        backend.error.connect(self._on_error)
        backend.verifyResult.connect(self._on_verify_result)
        backend.deviceFound.connect(self._on_device_found)
        backend.enrolledFingersChanged.connect(self._on_enrolled_fingers)

        backend.find_device()

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

    @Slot()
    def on_verify(self):
        self._backend.start_verify()

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

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
