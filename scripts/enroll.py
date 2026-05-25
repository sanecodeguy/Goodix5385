#!/usr/bin/env python3
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Enroll fingerprints using Goodix 5385")
    parser.add_argument("--outdir", default="enrolled", help="Output directory")
    parser.add_argument("--count", type=int, default=6, help="Number of captures")
    args = parser.parse_args()

    from goodix5385 import driver, matcher

    if os.path.exists(args.outdir):
        shutil.rmtree(args.outdir)
    os.makedirs(args.outdir, exist_ok=True)

    print("Initializing Goodix 5385 sensor...")
    device, calib_params = driver.initialize_device()

    clear_src = "clear.pgm"
    clear_dst = os.path.join(args.outdir, "clear.pgm")
    shutil.copy2(clear_src, clear_dst)

    print(f"\nCapturing {args.count} fingerprints...")
    for i in range(args.count):
        input(f"  Capture {i+1}/{args.count} — Place finger and press Enter...")
        raw_path = os.path.join(args.outdir, f"raw_{i}.pgm")
        driver.capture_fingerprint(device, calib_params, raw_path)
        print(f"    Saved: {raw_path}")

    print("\nBuilding composite template...")
    template_path = matcher.enroll_fingerprints(args.outdir, clear_pgm=clear_dst)
    if template_path is None:
        print("Enrollment FAILED")
        sys.exit(1)
    print(f"\nEnrollment complete! Composite template: {template_path}")


if __name__ == "__main__":
    main()
