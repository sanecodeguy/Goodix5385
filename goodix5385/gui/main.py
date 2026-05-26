#!/usr/bin/env python3
"""Goodix5385 Fingerprint Enrollment GUI — Qt/QML frontend for fprintd."""

import os
import sys

from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtGui import QIcon, QAction
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from .fprintd_dbus import FprintdBackend

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


class FprintBridge(QObject):
    def __init__(self, backend: FprintdBackend, engine: QQmlApplicationEngine,
                 tray: QSystemTrayIcon, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._engine = engine
        self._tray = tray
        self._root = None

        backend.enrolled.connect(self._on_enrolled)
        backend.stagePassed.connect(self._on_stage_passed)
        backend.retryScan.connect(self._on_retry)
        backend.error.connect(self._on_error)
        backend.verifyResult.connect(self._on_verify_result)
        backend.deviceFound.connect(self._on_device_found)

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

    def _on_stage_passed(self):
        overlay = self._get_overlay()
        if overlay:
            cnt = overlay.property("scanCount") + 1
            overlay.setProperty("scanCount", cnt)
            overlay.setProperty("status", "Fingerprint captured — lift and press again")

    def _on_retry(self, msg: str):
        overlay = self._get_overlay()
        if overlay:
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

    def _on_verify_result(self, matched: bool):
        overlay = self._get_overlay()
        if overlay:
            if matched:
                overlay.setProperty("success", True)
                overlay.setProperty("status", "Verified!")
            else:
                overlay.setProperty("status", "Not recognized — try again")

    @Slot(str)
    def on_enroll(self, finger: str):
        self._backend.start_enroll(finger)

    @Slot()
    def on_verify(self):
        self._backend.start_verify()

    @Slot()
    def on_stop(self):
        self._backend.stop_current()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Goodix5385 Fingerprint")
    app.setQuitOnLastWindowClosed(False)

    # Setup tray icon
    icon_path = os.path.join(ICON_DIR, "fingerprint.svg")
    tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    tray = QSystemTrayIcon()
    tray.setIcon(tray_icon)
    tray.setToolTip("Goodix5385 Fingerprint")

    menu = QMenu()
    enroll_action = QAction("Enroll Fingerprint")
    verify_action = QAction("Verify Fingerprint")
    quit_action = QAction("Quit")
    menu.addAction(enroll_action)
    menu.addAction(verify_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    # Setup backend and engine
    backend = FprintdBackend()
    engine = QQmlApplicationEngine()

    bridge = FprintBridge(backend, engine, tray)
    engine.rootContext().setContextProperty("fprintBridge", bridge)

    qml_path = QUrl.fromLocalFile(os.path.join(QML_DIR, "main.qml"))
    engine.load(qml_path)

    root_win = None
    if engine.rootObjects():
        root_win = engine.rootObjects()[0]

    if not root_win:
        print("Failed to load QML UI", file=sys.stderr)
        return 1

    # Connect tray menu actions
    def on_enroll_click():
        dlg = root_win.findChild(QObject, "fingerDialog")
        if dlg:
            dlg.open()
    enroll_action.triggered.connect(on_enroll_click)

    def on_verify_click():
        bridge.on_verify()
        overlay = bridge._get_overlay()
        if overlay:
            overlay.setProperty("isEnrolling", False)
            overlay.setProperty("fingerName", "")
            overlay.setProperty("success", False)
            overlay.setProperty("status", "Place your finger on the sensor")
            overlay.setProperty("scanCount", 0)
            overlay.show()
    verify_action.triggered.connect(on_verify_click)

    quit_action.triggered.connect(app.quit)

    tray.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
