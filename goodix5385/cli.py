import argparse
import os
import subprocess
import sys

from . import driver
from . import preprocessor
from . import config


def cmd_init(args):
    print("Initializing Goodix 5385 fingerprint sensor...")
    device, calib_params = driver.initialize_device()
    print("Device initialized successfully.")
    print("Calibration complete.")


def cmd_capture(args):
    print("Initializing device for capture...")
    device, calib_params = driver.initialize_device()

    output = args.output or "fingerprint.pgm"
    print(f"Capturing fingerprint to {output}...")
    print("Place your finger on the sensor.")
    driver.capture_fingerprint(device, calib_params, output)
    print(f"Fingerprint saved to {output}")


def cmd_enroll(args):
    print("Initializing device for enrollment...")
    device, calib_params = driver.initialize_device()

    os.makedirs(args.outdir, exist_ok=True)

    num_images = args.count
    print(f"Will capture {num_images} fingerprint images at different angles.")
    print("Follow the prompts to place your finger at different angles.")

    for i in range(num_images):
        input(f"\nPress Enter when ready for capture {i+1}/{num_images} "
              f"(angle: {args.angles[i] if i < len(args.angles) else 'auto'})...")
        raw_path = os.path.join(args.outdir, f"raw_{i}.pgm")
        processed_path = os.path.join(args.outdir, f"processed_{i}.pgm")
        clear_path = "clear.pgm"

        driver.capture_fingerprint(device, calib_params, raw_path)
        print(f"Raw capture saved: {raw_path}")

        if os.path.exists(clear_path):
            preprocessor.preprocess_image(clear_path, raw_path, processed_path.replace(".pgm", ""))
            print(f"Processed capture saved: {processed_path}")
        else:
            print("No clear image found, using raw image.")
            os.rename(raw_path, processed_path)

    print(f"\nEnrollment complete. {num_images} fingerprints saved to {args.outdir}")

    if args.compute_sigfm:
        print("Computing SIGFM templates...")
        sigfm_bin = os.path.join(os.path.dirname(__file__), "..", "sigfm", "compute.out")
        if os.path.exists(sigfm_bin):
            subprocess.run([sigfm_bin], cwd=args.outdir)
            print("SIGFM templates computed.")
        else:
            print("SIGFM binary not found. Build it with: make -C sigfm")


def cmd_authenticate(args):
    if not args.templates:
        print("Error: --templates directory required")
        sys.exit(1)

    print("Initializing device...")
    device, calib_params = driver.initialize_device()

    raw_path = "auth_raw.pgm"
    processed_path = "auth_processed.pgm"
    clear_path = "clear.pgm"

    print("Place your finger on the sensor for authentication...")
    driver.capture_fingerprint(device, calib_params, raw_path)

    if os.path.exists(clear_path):
        result_path = preprocessor.preprocess_image(clear_path, raw_path, "auth_processed")
    else:
        result_path = raw_path

    print("Running SIGFM matching...")
    sigfm_bin = os.path.join(os.path.dirname(__file__), "..", "sigfm", "match.out")
    if os.path.exists(sigfm_bin):
        result = subprocess.run(
            [sigfm_bin, result_path, clear_path, args.templates],
            capture_output=True, text=True)
        match = result.stdout.strip()
        print(f"Matching result: {match}")
        if match == "1":
            print("AUTHENTICATION SUCCESSFUL - Fingerprint matched!")
        else:
            print("AUTHENTICATION FAILED - Fingerprint did not match.")
    else:
        print("SIGFM binary not found. Build it with: make -C sigfm")


def cmd_preprocess(args):
    result = preprocessor.preprocess_image(args.background, args.image, args.output)
    print(f"Preprocessed image saved to: {result}")


def main():
    parser = argparse.ArgumentParser(description="Goodix 5385 Fingerprint Tool")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize and calibrate the sensor")
    init_parser.set_defaults(func=cmd_init)

    capture_parser = subparsers.add_parser("capture", help="Capture a single fingerprint")
    capture_parser.add_argument("-o", "--output", default="fingerprint.pgm")
    capture_parser.set_defaults(func=cmd_capture)

    enroll_parser = subparsers.add_parser("enroll", help="Enroll multiple fingerprints")
    enroll_parser.add_argument("--outdir", default="enrolled")
    enroll_parser.add_argument("--count", type=int, default=5)
    enroll_parser.add_argument("--angles", nargs="*", default=[])
    enroll_parser.add_argument("--compute-sigfm", action="store_true")
    enroll_parser.set_defaults(func=cmd_enroll)

    auth_parser = subparsers.add_parser("authenticate", help="Authenticate against enrolled templates")
    auth_parser.add_argument("--templates", required=True)
    auth_parser.set_defaults(func=cmd_authenticate)

    preprocess_parser = subparsers.add_parser("preprocess", help="Preprocess a fingerprint image")
    preprocess_parser.add_argument("background")
    preprocess_parser.add_argument("image")
    preprocess_parser.add_argument("-o", "--output", default="processed")
    preprocess_parser.set_defaults(func=cmd_preprocess)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
