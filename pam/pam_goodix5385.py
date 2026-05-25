#!/usr/bin/env python3
"""PAM module for Goodix 5385 fingerprint authentication.

Install:
  sudo cp pam_goodix5385.py /usr/local/bin/
  sudo chmod +x /usr/local/bin/pam_goodix5385.py

Then add to /etc/pam.d/:
  auth sufficient pam_exec.so /usr/local/bin/pam_goodix5385.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, "/usr/local/share/goodix5385")


def authenticate():
    from goodix5385 import driver, preprocessor, matcher

    templates_dir = os.path.expanduser("~/.goodix5385/enrolled")
    template_path = os.path.join(templates_dir, "templates.pkl")
    clear_path = os.path.join(templates_dir, "clear.pgm")

    if not os.path.exists(template_path):
        return False

    device, calib_params = driver.initialize_device()

    raw_path = "/tmp/pam_auth_raw.pgm"
    processed_path = "/tmp/pam_auth_processed"

    driver.capture_fingerprint(device, calib_params, raw_path)

    if os.path.exists(clear_path):
        result_path = preprocessor.preprocess_image(clear_path, raw_path, processed_path)
        return matcher.authenticate_fingerprint(result_path, template_path, clear_path)

    proj_clear = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clear.pgm")
    if os.path.exists(proj_clear):
        return matcher.authenticate_fingerprint(raw_path, template_path, proj_clear)

    return matcher.authenticate_fingerprint(raw_path, template_path)


if __name__ == "__main__":
    sys.exit(0 if authenticate() else 1)
