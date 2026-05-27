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
                    proc = subprocess.Popen(
                        ["fprintd-verify"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )

                    outcome = None  # 'match' | 'nomatch' | 'retry' | 'error'

                    for line in proc.stdout:
                        if gen != self._verify_gen:
                            proc.terminate()
                            proc.wait()
                            return

                        line = line.strip()

                        if "verify-match" in line:
                            outcome = 'match'
                            proc.terminate()
                            break
                        elif "verify-no-match" in line:
                            outcome = 'nomatch'
                            proc.terminate()
                            break
                        elif "verify-retry-scan" in line:
                            outcome = 'retry'
                            proc.terminate()
                            break
                        elif "verify-unknown" in line:
                            outcome = 'error'
                            proc.terminate()
                            break
                        elif "failed" in line.lower() and "error" in line.lower():
                            outcome = 'error'
                            proc.terminate()
                            break

                    # Drain and reap — but don't block long; timeout after 0.5s
                    try:
                        proc.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()

                except Exception as e:
                    self.error.emit(str(e))
                    return

                if gen != self._verify_gen:
                    return

                if outcome == 'match':
                    self.verifyResult.emit(True)
                    return
                elif outcome == 'nomatch':
                    # Emit no-match immediately so UI shows feedback,
                    # then loop back instantly — no sleep needed.
                    self.retryScan.emit("Not recognized — try again")
                    # fall through to loop and restart immediately
                elif outcome == 'retry':
                    self.retryScan.emit("Lift and re-press your finger")
                    # fall through to loop and restart immediately
                elif outcome == 'error':
                    self.error.emit("Verification error")
                    return
                else:
                    # Process ended without any recognised line — restart
                    self.retryScan.emit("Scan not detected — try again")

                # Brief yield so fprintd has time to release the device lock
                # before we re-open it.  50 ms is enough; 1000ms was the killer.
                import time
                time.sleep(0.05)

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
