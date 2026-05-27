"""Backend for fingerprint operations using fprintd CLI tools via subprocess."""

import subprocess
import sys
import threading
import time

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
        self._verify_gen = 0
        self._verify_result = False

    def _parse_enrolled_fingers(self, output: str):
        fingers = []
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('- #') and ':' in line:
                finger_part = line.split(':', 1)[1].strip()
                fingers.append(finger_part)
        self.enrolledFingersChanged.emit(fingers)

    def find_device(self):
        try:
            import getpass
            result = subprocess.run(
                ["fprintd-list", getpass.getuser()],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0 or "No devices" in result.stdout:
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

        def run():
            try:
                proc = subprocess.Popen(
                    ["fprintd-enroll", "--finger", finger],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
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

        self._verify_gen += 1
        gen = self._verify_gen

        def run():
            while True:
                if gen != self._verify_gen:
                    return

                proc = None
                try:
                    cmd = ["fprintd-verify"]
                    if finger:
                        cmd.extend(["--finger", finger])
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )

                    for line in proc.stdout:
                        if gen != self._verify_gen:
                            proc.terminate()
                            return

                        line = line.strip()

                        if "verify-match" in line:
                            proc.terminate()
                            try: proc.wait(timeout=0.3)
                            except: proc.kill(); proc.wait()
                            self.verifyResult.emit(True)
                            return
                        elif "verify-no-match" in line or "verify-unknown" in line:
                            proc.terminate()
                            try: proc.wait(timeout=0.3)
                            except: proc.kill(); proc.wait()
                            self.retryScan.emit("Not recognized — try again")
                            time.sleep(0.2)
                            break
                        elif "verify-retry-scan" in line:
                            self.retryScan.emit("Lift and re-press your finger")
                            continue
                        elif "failed" in line.lower() and "error" in line.lower():
                            self.retryScan.emit("Device error — resetting sensor...")
                            subprocess.run(["pkill", "fprintd"], capture_output=True)
                            subprocess.run([sys.executable, "-m", "goodix5385.scripts.usb_reset"], capture_output=True)
                            time.sleep(1.0)
                            break

                except Exception as e:
                    self.error.emit(str(e))
                    return

        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def stop_current(self):
        self._verify_gen += 1
        subprocess.run(["pkill", "-f", "fprintd-enroll"], capture_output=True)
        subprocess.run(["pkill", "-f", "fprintd-verify"], capture_output=True)

    @Slot(str)
    def delete_finger(self, finger: str):
        import getpass
        try:
            subprocess.run(
                ["fprintd-delete", getpass.getuser(), "--finger", finger],
                capture_output=True, timeout=10
            )
            self.find_device()
        except Exception as e:
            self.error.emit(str(e))
