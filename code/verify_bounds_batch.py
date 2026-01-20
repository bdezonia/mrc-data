#!/usr/bin/env python3
"""
verify_batch.py

Batch verifier: runs verify_csv.py over all *.csv files in a directory.
Exits non-zero only if HARD invariants fail.

Usage:
  python verify_batch.py data/
"""

import glob
import os
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 verify_bounds_batch.py <directory>")
        sys.exit(1)

    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"ERROR: {root} is not a directory")
        sys.exit(1)

    csv_files = sorted(glob.glob(os.path.join(root, "*.csv")))
    if not csv_files:
        print("No CSV files found.")
        sys.exit(1)

    ok, bad = [], []

    for path in csv_files:
        print("=" * 72)
        print(f"Checking {path}")
        proc = subprocess.run(["python3", "verify_bounds.py", path], text=True)
        if proc.returncode == 0:
            ok.append(path)
        else:
            bad.append((path, proc.returncode))

    print("\n" + "=" * 72)
    print("BATCH VERIFICATION SUMMARY")
    print("=" * 72)
    print(f"Total checked : {len(csv_files)}")
    print(f"Passed (hard) : {len(ok)}")
    print(f"Failed (hard) : {len(bad)}")

    if bad:
        print("\nFAILED FILES (hard invariant violations):")
        for path, rc in bad:
            print(f"  {path}  (exit={rc})")
        sys.exit(1)

    print("\nAll files passed hard verification.")
    sys.exit(0)


if __name__ == "__main__":
    main()
