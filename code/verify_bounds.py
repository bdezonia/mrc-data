#!/usr/bin/env python3
"""
verify_bounds.py

Checks amin/amax closed forms against true DP support.

Hard checks: none (data correctness assumed)
Soft checks (reported, not fatal to data):
  - amin(r,c,o) vs true amin
  - amax(r,c,o) vs true amax

Exit code:
  0 = no mismatches
  1 = at least one mismatch
"""

import csv
import sys
from typing import Dict, Tuple

import acode   # expects amin, amax


def grid_maxA(r, c):
    return 2 * r * c - r - c


def read_dense_csv(path):
    with open(path, "r") as f:
        lines = f.read().splitlines()

    if not lines or lines[-1].strip() != ".DONE.":
        raise ValueError("File does not end with .DONE.")

    reader = csv.reader(lines[:-1])
    header = next(reader, None)
    if header != ["r", "c", "o", "a", "count"]:
        raise ValueError(f"Bad header: {header}")

    table: Dict[Tuple[int, int], int] = {}
    r = c = None

    for row in reader:
        rr, cc, o, a, cnt = map(int, row)
        if r is None:
            r, c = rr, cc
        if rr != r or cc != c:
            raise ValueError("Mixed (r,c) values in file.")
        table[(o, a)] = cnt

    return r, c, table


def true_support(tab, r, c):
    """
    Returns:
      amin_true[o], amax_true[o] for all o
    """
    n = r * c
    maxA = grid_maxA(r, c)

    amin = [None] * (n + 1)
    amax = [None] * (n + 1)

    for o in range(n + 1):
        lo = None
        hi = None
        for a in range(maxA + 1):
            if tab[(o, a)] > 0:
                if lo is None:
                    lo = a
                hi = a
        amin[o] = lo
        amax[o] = hi

    return amin, amax


def verify(path, show=False, max_show=20):
    print(f"\nChecking bounds: {path}")

    try:
        r, c, tab = read_dense_csv(path)
    except Exception as e:
        print(f"❌ ERROR reading file: {e}")
        return 2

    amin_true, amax_true = true_support(tab, r, c)

    n = r * c
    bad_amin = []
    bad_amax = []

    for o in range(n + 1):
        a_cf = acode.amin(r, c, o)
        A_cf = acode.amax(r, c, o)

        if amin_true[o] != a_cf:
            bad_amin.append((o, amin_true[o], a_cf))

        if amax_true[o] != A_cf:
            bad_amax.append((o, amax_true[o], A_cf))

    if not bad_amin and not bad_amax:
        print("✅ No amin/amax mismatches.")
        return 0

    print("❌ MISMATCHES FOUND")

    if bad_amin:
        print(f"  amin mismatches: {len(bad_amin)}")
        if show:
            for o, t, ccf in bad_amin[:max_show]:
                print(f"    o={o:3d}  true={t:3d}  cf={ccf:3d}")

    if bad_amax:
        print(f"  amax mismatches: {len(bad_amax)}")
        if show:
            for o, t, ccf in bad_amax[:max_show]:
                print(f"    o={o:3d}  true={t:3d}  cf={ccf:3d}")

    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 verify_bounds.py <r.c.csv> [--show]")
        sys.exit(1)

    path = sys.argv[1]
    show = "--show" in sys.argv

    sys.exit(verify(path, show=show))

