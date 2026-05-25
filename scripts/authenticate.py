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

    from goodix5385 import driver, preprocessor, matcher

    template_path = os.path.join(args.templates, "templates.pkl")
    if not os.path.exists(template_path):
        print(f"Error: no templates found at {template_path}")
        print("Run enrollment first: python scripts/enroll.py")
        sys.exit(1)

    print("Initializing Goodix 5385 sensor...")
    device, calib_params = driver.initialize_device()

    raw_path = "/tmp/auth_raw.pgm"
    processed_path = "/tmp/auth_processed"
    clear_path = os.path.join(args.templates, "clear.pgm")

    print("\nPlace your finger on the sensor for authentication...")
    driver.capture_fingerprint(device, calib_params, raw_path)

    if not os.path.exists(clear_path):
        print("No clear.pgm found in templates dir")
        sys.exit(1)

    result_path = preprocessor.preprocess_image(clear_path, raw_path, processed_path)
    print(f"Preprocessed image saved to {result_path}")

    result = matcher.authenticate_fingerprint(result_path, template_path)

    if result:
        print("\nAUTHENTICATION SUCCESSFUL - Fingerprint matched!")
        return 0
    else:
        print("\nAUTHENTICATION FAILED - Fingerprint did not match.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
