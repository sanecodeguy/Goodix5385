#!/usr/bin/env python3
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Capture a raw fingerprint image")
    parser.add_argument("-o", "--output", default="fingerprint.pgm",
                        help="Output PGM file path")
    args = parser.parse_args()

    from goodix5385 import driver

    print("Initializing Goodix 5385 sensor...")
    device, calib_params = driver.initialize_device()

    print(f"\nPlace your finger on the sensor to capture to {args.output}...")
    driver.capture_fingerprint(device, calib_params, args.output)
    print(f"\nFingerprint saved to {args.output}")


if __name__ == "__main__":
    main()
