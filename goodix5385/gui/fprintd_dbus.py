"""Backend for fingerprint operations using fprintd CLI tools via subprocess."""

import subprocess
import threading

from PySide6.QtCore import QObject, Signal, Slot


class FprintdBackend(QObject):
    enrolled = Signal()
    verifyResult = Signal(bool)
    stagePassed = Signal()
    retryScan = Signal(str)
    error = Signal(str)
    deviceFound = Signal(bool)
    enrolledFingersChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False
        self._verify_result = False

    def _parse_enrolled_fingers(self, output: str):
        fingers = []
        for line in output.split('\n'):
            line = line.strip()
            if ' - #' in line and ':' in line:
                finger_part = line.split(':', 1)[1].strip()
                finger_name = finger_part.replace('-', ' ').title()
                fingers.append(finger_name)
        self.enrolledFingersChanged.emit(fingers)

    def find_device(self):
        try:
            result = subprocess.run(
                ["fprintd-list"],
                capture_output=True, text=True, timeout=5
            )
            if "No devices" in result.stderr or "No devices" in result.stdout:
                self.deviceFound.emit(False)
                self.error.emit("No fingerprint devices found")
                return False
            self.deviceFound.emit(True)
            self._parse_enrolled_fingers(result.stdout)
            return True
        except FileNotFoundError:
            self.deviceFound.emit(False)
            self.error.emit("fprintd not installed")
            return False
        except subprocess.TimeoutExpired:
            self.deviceFound.emit(False)
            self.error.emit("fprintd not responding")
            return False

    @Slot(str)
    def start_enroll(self, finger="right-index-finger"):
        if not self.find_device():
            return

        self._stop = False

        def run():
            try:
                proc = subprocess.Popen(
                    ["fprintd-enroll", "--finger", finger],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    if self._stop:
                        proc.terminate()
                        return
                    line = line.strip()
                    if "Enroll result: enroll-stage-passed" in line:
                        self.stagePassed.emit()
                    elif "Enroll result: enroll-completed" in line:
                        self.enrolled.emit()
                        return
                    elif "Enroll result: enroll-failed" in line:
                        self.error.emit("Enrollment failed")
                        return
                    elif "Enroll result: enroll-retry-scan" in line:
                        self.retryScan.emit("Lift and re-press your finger")
                    elif "Enroll result: enroll-data-full" in line:
                        self.enrolled.emit()
                        return
                    elif "failed" in line.lower() and "error" in line.lower():
                        self.error.emit(line)
                        return
                proc.wait()
            except Exception as e:
                self.error.emit(str(e))

        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def start_verify(self, finger=""):
        if not self.find_device():
            return

        self._stop = False

        def run():
            while not self._stop:
                try:
                    proc = subprocess.Popen(
                        ["fprintd-verify"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )
                    matched = False
                    for line in proc.stdout:
                        if self._stop:
                            proc.terminate()
                            return
                        line = line.strip()
                        if "verify-match" in line:
                            self.verifyResult.emit(True)
                            matched = True
                            break
                        elif "verify-no-match" in line:
                            self.retryScan.emit("Not recognized — press sensor again")
                            break
                        elif "verify-retry-scan" in line:
                            self.retryScan.emit("Lift and re-press your finger")
                        elif "verify-unknown" in line:
                            self.error.emit("Verification error")
                            return
                        elif "failed" in line.lower() and "error" in line.lower():
                            self.error.emit(line)
                            return
                    proc.wait()
                    if matched or self._stop:
                        return
                except Exception as e:
                    self.error.emit(str(e))
                    return

        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def stop_current(self):
        self._stop = True
        subprocess.run(["pkill", "-f", "fprintd-enroll"], capture_output=True)
        subprocess.run(["pkill", "-f", "fprintd-verify"], capture_output=True)
