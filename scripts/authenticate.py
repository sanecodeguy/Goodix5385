#!/usr/bin/env python3
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Authenticate fingerprint")
    parser.add_argument("--templates", default="enrolled",
                        help="Directory with templates.pkl and clear.pgm")
    args = parser.parse_args()

    from goodix5385 import driver, matcher

    template_path = os.path.join(args.templates, "templates.pkl")
    if not os.path.exists(template_path):
        print(f"Error: no templates found at {template_path}")
        print("Run enrollment first: python scripts/enroll.py")
        sys.exit(1)

    print("Initializing Goodix 5385 sensor...")
    device, calib_params = driver.initialize_device()

    clear_path = os.path.join(args.templates, "clear.pgm")
    if not os.path.exists(clear_path):
        print("No clear.pgm in templates dir")
        sys.exit(1)

    successes = 0
    attempts = 3

    for i in range(attempts):
        print(f"\nCapture {i+1}/{attempts} — Place finger on sensor...")
        raw_path = f"/tmp/auth_raw_{i}.pgm"
        driver.capture_fingerprint(device, calib_params, raw_path)

        result = matcher.authenticate_fingerprint(raw_path, template_path,
                                                    clear_pgm=clear_path)
        if result:
            successes += 1
            print(f"  Capture {i+1}: MATCH")
        else:
            print(f"  Capture {i+1}: no match")

    print(f"\n{successes}/{attempts} captures matched")
    if successes >= 2:
        print("AUTHENTICATION SUCCESSFUL")
        return 0
    else:
        print("AUTHENTICATION FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
