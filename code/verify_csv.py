#!/usr/bin/env python3
"""
verify_csv.py  (DENSE-ONLY, DATA-CORRECTNESS)

Hard checks:
  - header correctness
  - .DONE. sentinel
  - dense shape
  - (r,c) consistency
  - row ranges
  - sum_{o,a} = 2^(r*c)
  - sum_a(o) = C(r*c, o)
  - boundary values

"""

import csv
import math
import sys
from typing import Dict, Tuple


def grid_maxA(r, c):
    return 2 * r * c - r - c


def binom(n, k):
    return math.comb(n, k)


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


def verify(path):
    print(f"\nVerifying: {path}")

    try:
        r, c, tab = read_dense_csv(path)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 2

    n = r * c
    maxA = grid_maxA(r, c)

    expected = (n + 1) * (maxA + 1)
    if len(tab) != expected:
        print(f"❌ ERROR: Expected {expected} rows, found {len(tab)}")
        return 2

    print("ℹ️  Dense format confirmed.")

    total = 0
    per_o = [0] * (n + 1)

    for (o, a), cnt in tab.items():
        if not (0 <= o <= n and 0 <= a <= maxA):
            print(f"❌ ERROR: Out-of-range (o,a)=({o},{a})")
            return 2
        if cnt < 0:
            print(f"❌ ERROR: Negative count at ({o},{a})")
            return 2
        total += cnt
        per_o[o] += cnt

    if total != (1 << n):
        print(f"❌ ERROR: sum(count)={total}, expected 2^{n}")
        return 2
    print("✅ sum(count) = 2^(r*c)")

    bad = 0
    for o in range(n + 1):
        want = binom(n, o)
        if per_o[o] != want:
            if bad < 10:
                print(f"❌ ERROR: sum_a(o={o})={per_o[o]}, expected {want}")
            bad += 1
    if bad:
        print(f"❌ ERROR: per-o sums failed for {bad} values")
        return 2
    print("✅ per-o sums match binomial coefficients")

    if tab[(0, 0)] != 1 or tab[(n, maxA)] != 1:
        print("❌ ERROR: Boundary conditions failed")
        return 2
    print("✅ boundary conditions OK")

    print("✅ verification passed (data correctness)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 verify_csv.py <r.c.csv>")
        sys.exit(1)

    sys.exit(verify(sys.argv[1]))
