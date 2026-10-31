#!/usr/bin/env python3
"""Exact null-model statistics for m(r,c,o,a), read from mrc-data CSV tables.

Requires Python 3.9+; no third-party dependencies. This does NOT generate MRC counts.
The null model uniformly selects o occupied cells from an r x c rectangle.
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
from math import comb
import json
import os
from pathlib import Path
import sys
from typing import Dict, Optional


class MRCDataError(Exception):
    """Missing/incomplete/invalid MRC table or unsupported request."""


def locate_csv(directory: Path, r: int, c: int) -> Path:
    """Respect m(r,c,o,a) = m(c,r,o,a) and older filename orientations."""
    candidates = [directory / f"{r}.{c}.csv", directory / f"{c}.{r}.csv"]
    for path in candidates:
        if path.is_file():
            return path
    raise MRCDataError(
        "Missing table for %dx%d. Tried: %s" %
        (r, c, ", ".join(str(p) for p in dict.fromkeys(candidates)))
    )


def read_occupancy(path: Path, r: int, c: int, o: int) -> Dict[int, int]:
    """Scan a completed CSV, retaining only counts for occupancy o.

    Accept sparse or dense records: omitted a entries mean zero only if the
    occupancy's count sum passes the exact normalization check below.
    The inline .DONE. is mandatory: a half-written file must not pass silently.
    A companion .DONE file, when present, is not a substitute for inline EOF.
    """
    counts: Dict[int, int] = {}
    dims = {(r, c), (c, r)}
    n = r * c
    max_edges = 2 * n - r - c
    done = False
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise MRCDataError(f"Empty file: {path}")
            if [col.strip() for col in header] != ["r", "c", "o", "a", "count"]:
                raise MRCDataError(f"Unexpected header in {path}: {header!r}")
            for line_num, row in enumerate(reader, start=2):
                if not row or all(not cell.strip() for cell in row):
                    continue
                if row == [".DONE."]:
                    done = True
                    # Only whitespace is permitted beyond the sentinel.
                    for tail in reader:
                        if tail and any(cell.strip() for cell in tail):
                            raise MRCDataError(
                                f"Nonblank line after .DONE. in {path}"
                            )
                    break
                if len(row) != 5:
                    raise MRCDataError(
                        f"Malformed row {line_num} in {path}: {row!r}"
                    )
                try:
                    rr, cc, oo, aa, count = (int(v.strip()) for v in row)
                except ValueError as exc:
                    raise MRCDataError(
                        f"Non-integer row {line_num} in {path}: {row!r}"
                    ) from exc
                if (rr, cc) not in dims:
                    raise MRCDataError(
                        f"Dimension mismatch on row {line_num} in {path}: {rr}x{cc}"
                    )
                if not (0 <= oo <= n and 0 <= aa <= max_edges and count >= 0):
                    raise MRCDataError(f"Out-of-range row {line_num} in {path}")
                if oo == o:
                    if aa in counts:
                        raise MRCDataError(
                            f"Duplicate occupancy/coupling entry ({o},{aa}) in {path}"
                        )
                    counts[aa] = count
    except OSError as exc:
        raise MRCDataError(f"Could not read {path}: {exc}") from exc
    if not done:
        raise MRCDataError(f"No terminal .DONE. sentinel in {path}; file may be incomplete")
    if not counts:
        raise MRCDataError(f"No records for occupancy o={o} in {path}")
    total = sum(counts.values())
    expected = comb(n, o)
    if total != expected:
        raise MRCDataError(
            f"Normalization FAILED at occupancy {o} in {path}: "
            f"sum_a m={total}, expected C({n},{o})={expected}"
        )
    return counts


def falling_probability(k: int, n: int, o: int) -> Fraction:
    """Probability that k distinct specified cells are all occupied."""
    if k > n or k > o:
        return Fraction(0)
    result = Fraction(1)
    for i in range(k):
        result *= Fraction(o - i, n - i)
    return result


def theoretical_moments(r: int, c: int, o: int):
    """Exact mean/variance of occupied-neighbor edge count.

    E = number of grid edges; S = number of unordered pairs of distinct
    edges sharing one vertex. Expand A^2 using edge-indicator variables.
    """
    n = r * c
    edges = r * (c - 1) + c * (r - 1)
    if min(r, c) == 1:
        shared = max(n - 2, 0)
    else:
        shared = 4 + 3 * (2 * (r - 2) + 2 * (c - 2)) + 6 * (r - 2) * (c - 2)
    disjoint = comb(edges, 2) - shared
    if disjoint < 0:
        raise AssertionError("Internal graph edge pair count error")
    p2 = falling_probability(2, n, o)
    p3 = falling_probability(3, n, o)
    p4 = falling_probability(4, n, o)
    mean = edges * p2
    second = edges * p2 + 2 * shared * p3 + 2 * disjoint * p4
    variance = second - mean * mean
    if variance < 0:
        raise AssertionError("Internal theoretical variance error")
    return mean, variance


def rational_json(value: Fraction) -> dict:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def decimal_value(value: Fraction, precision: int) -> str:
    with localcontext() as ctx:
        ctx.prec = max(precision + 15, 50)
        dec = Decimal(value.numerator) / Decimal(value.denominator)
        return format(dec, f".{precision}g")


def decimal_sqrt(value: Fraction, precision: int) -> str:
    with localcontext() as ctx:
        ctx.prec = max(precision + 15, 50)
        dec = (Decimal(value.numerator) / Decimal(value.denominator)).sqrt()
        return format(dec, f".{precision}g")


def z_decimal(value: Fraction, variance: Fraction, precision: int) -> str:
    with localcontext() as ctx:
        ctx.prec = max(precision + 15, 50)
        diff = Decimal(value.numerator) / Decimal(value.denominator)
        sigma = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        return format(diff / sigma, f".{precision}g")


def quantile(sorted_nonzero: list, countmap: Dict[int, int], total: int,
             p: Fraction) -> int:
    """Exact discrete quantile, smallest a with P(A<=a)>=p."""
    cumulative = 0
    for k in sorted_nonzero:
        cumulative += countmap[k]
        if Fraction(cumulative, total) >= p:
            return k
    return sorted_nonzero[-1]


def calculate_statistics(r: int, c: int, o: int, a: int,
                         countmap: Dict[int, int], precision: int = 16) -> dict:
    n = r * c
    total = comb(n, o)
    edges = 2 * n - r - c
    if not (r > 0 and c > 0 and 0 <= o <= n and 0 <= a <= edges):
        raise MRCDataError("Invalid dimensions, occupancy, or coupling count")
    if sum(countmap.values()) != total:
        raise MRCDataError("Occupancy distribution is not normalized")
    nonzero = sorted(k for k, v in countmap.items() if v > 0)
    if not nonzero:
        raise MRCDataError("No attainable coupling counts for this occupancy")
    amin, amax = nonzero[0], nonzero[-1]
    mass = countmap.get(a, 0)
    less = sum(w for k, w in countmap.items() if k < a)
    greater = total - less - mass
    mean = Fraction(sum(k * w for k, w in countmap.items()), total)
    second = Fraction(sum(k * k * w for k, w in countmap.items()), total)
    variance = second - mean * mean
    theo_mean, theo_var = theoretical_moments(r, c, o)
    if mean != theo_mean or variance != theo_var:
        raise MRCDataError(
            "Exact moment checks FAILED: archive differs from the known "
            "mean/variance for fixed-occupancy random placement"
        )
    if variance < 0:
        raise MRCDataError("Negative variance in data")

    fractions = {
        "pmf": Fraction(mass, total),
        "cdf_le": Fraction(less + mass, total),
        "tail_ge": Fraction(greater + mass, total),
        "tail_lt": Fraction(less, total),
        "tail_gt": Fraction(greater, total),
        "midrank_percentile": Fraction(2 * less + mass, 2 * total),
    }

    # A valid exact two-sided p-value using distance from the NULL mean;
    # this avoids a (generally invalid) normal-tail approximation.
    target_dist = abs(Fraction(a) - mean)
    two_sided_count = sum(
        w for k, w in countmap.items()
        if abs(Fraction(k) - mean) >= target_dist
    )
    fractions["two_sided_distance_p"] = Fraction(two_sided_count, total)
    # Alternative discrete two-sided convention: probability ordering.
    fractions["two_sided_probability_order_p"] = Fraction(
        sum(w for w in countmap.values() if w <= mass), total
    )

    attainable = mass > 0
    span = amax - amin
    bounded = Fraction(a - amin, span) if attainable and span else None
    # Mean-centered bounded deviation; 0 at null mean, -1/+1 at endpoints.
    centered = None
    if attainable and variance > 0:
        if Fraction(a) >= mean:
            centered = (Fraction(a) - mean) / (Fraction(amax) - mean)
        else:
            centered = (Fraction(a) - mean) / (mean - Fraction(amin))

    z_score = z_decimal(Fraction(a) - mean, variance, precision) if variance > 0 else None
    z_min = z_decimal(Fraction(amin) - mean, variance, precision) if variance > 0 else None
    z_max = z_decimal(Fraction(amax) - mean, variance, precision) if variance > 0 else None
    mode_height = max(countmap.values())
    modes = [k for k in nonzero if countmap[k] == mode_height]
    q_specs = [("q025", "0.025"), ("q05", "0.05"), ("q25", "0.25"),
               ("median", "0.5"), ("q75", "0.75"), ("q95", "0.95"),
               ("q975", "0.975")]

    return {
        "r": r, "c": c, "o": o, "a": a,
        "n_cells": n, "possible_edges": edges,
        "occupancy_fraction": decimal_value(Fraction(o, n), precision),
        "count": str(mass), "total_placements": str(total),
        "attainable": attainable, "amin": amin, "amax": amax,
        "support_size": len(nonzero),
        "mean": decimal_value(mean, precision),
        "mean_exact": rational_json(mean),
        "variance": decimal_value(variance, precision),
        "variance_exact": rational_json(variance),
        "stddev": decimal_sqrt(variance, precision),
        "z_score": z_score, "z_min": z_min, "z_max": z_max,
        "bounded_aggregation": decimal_value(bounded, precision) if bounded is not None else None,
        "bounded_centered_deviation": decimal_value(centered, precision) if centered is not None else None,
        "mode": modes,
        "quantiles": {name: quantile(nonzero, countmap, total, Fraction(p)) for name, p in q_specs},
        "probabilities": {
            name: {"decimal": decimal_value(fr, precision), "exact": rational_json(fr)}
            for name, fr in fractions.items()
        },
    }


def write_distribution(path: Path, r: int, c: int, o: int,
                       countmap: Dict[int, int], precision: int) -> None:
    """Export distribution for this occupancy, including unattainable a gaps."""
    total = comb(r * c, o)
    cumulative = 0
    edge_count = 2 * r * c - r - c
    try:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["r", "c", "o", "a", "count", "probability", "cdf_le", "tail_ge"])
            for k in range(edge_count + 1):
                mass = countmap.get(k, 0)
                cumulative += mass
                writer.writerow([
                    r, c, o, k, mass,
                    decimal_value(Fraction(mass, total), precision),
                    decimal_value(Fraction(cumulative, total), precision),
                    decimal_value(Fraction(total - cumulative + mass, total), precision),
                ])
    except OSError as exc:
        raise MRCDataError(f"Unable to export distribution: {exc}") from exc


def guess_data_dir() -> Path:
    if os.environ.get("MRC_DATA_DIR"):
        return Path(os.environ["MRC_DATA_DIR"]).expanduser()
    guesses = [Path.cwd() / "data", Path(__file__).resolve().parent / "data",
               Path.home() / "dev" / "mrc-data" / "data"]
    return next((p for p in guesses if p.is_dir()), guesses[0])


def format_output(result: dict, file_path: Path) -> str:
    p = result["probabilities"]
    val = lambda key: p[key]["decimal"]
    fmt = lambda x: x if x is not None else "N/A (zero variance or degenerate bounds)"
    q = result["quantiles"]
    lines = [
        f"MRC exact statistics: (r,c,o,a)=({result['r']},{result['c']},{result['o']},{result['a']})",
        f"Source: {file_path}",
        "Null model: uniformly random placement of o occupied cells among rc cells",
        f"Cells: {result['n_cells']}   Occupancy fraction: {result['occupancy_fraction']}",
        f"Potential neighbor edges: {result['possible_edges']}",
        f"Achievable couplings: [{result['amin']}, {result['amax']}] "
        f"({result['support_size']} distinct values)",
        f"Observed configurations m(r,c,o,a): {result['count']}",
        f"Total configurations C(rc,o):       {result['total_placements']}",
        f"Attainable at fixed occupancy: {'yes' if result['attainable'] else 'NO (count is zero)'}",
        "",
        "EXACT NULL PROBABILITIES (decimal approximations shown)",
        f"  P(A = a):                 {val('pmf')}",
        f"  P(A <= a):                {val('cdf_le')}",
        f"  P(A >= a):                {val('tail_ge')}",
        f"  P(A < a):                 {val('tail_lt')}",
        f"  P(A > a):                 {val('tail_gt')}",
        f"  Midrank percentile:       {val('midrank_percentile')}  (multiply by 100 for %)",
        f"  Two-sided p (distance):   {val('two_sided_distance_p')}",
        f"  Two-sided p (mass order): {val('two_sided_probability_order_p')}",
        "",
        "REFERENCE DISTRIBUTION",
        f"  Mean couplings:           {result['mean']}",
        f"  Variance:                 {result['variance']}",
        f"  Standard deviation:       {result['stddev']}",
        f"  Mode(s):                  {', '.join(str(v) for v in result['mode'])}",
        f"  Quantiles (2.5/5/25/50/75/95/97.5%): "
        f"{q['q025']}/{q['q05']}/{q['q25']}/{q['median']}/{q['q75']}/{q['q95']}/{q['q975']}",
        "",
        "AGGREGATION SCORES",
        f"  Ordinary z-score:         {fmt(result['z_score'])}",
        f"  Achievable z range:       [{fmt(result['z_min'])}, {fmt(result['z_max'])}]",
        f"  Bounded aggregation [0,1]:{(' ' + fmt(result['bounded_aggregation']))}",
        f"  Mean-centered score [-1,1]: {fmt(result['bounded_centered_deviation'])}",
    ]
    if not result["attainable"]:
        lines.append("  NOTE: This coupling count is impossible at the specified occupancy.")
    lines.append("Notes: z is NOT assumed normally distributed. P-values are exact under the stated null model.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Exact statistics from completed mrc-data CSV tables (no DP, stdlib only)."
    )
    ap.add_argument("r", type=int, help="Grid rows")
    ap.add_argument("c", type=int, help="Grid columns")
    ap.add_argument("o", type=int, help="Number of occupied cells")
    ap.add_argument("a", type=int, help="Observed number of couplings")
    ap.add_argument("--data-dir", type=Path, default=guess_data_dir(),
                    help="Directory containing R.C.csv; default: MRC_DATA_DIR, ./data, or ~/dev/mrc-data/data")
    ap.add_argument("--precision", type=int, default=16,
                    help="Significant decimal digits shown (default 16)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON, including exact rational probabilities")
    ap.add_argument("--export-csv", type=Path, metavar="FILE",
                    help="Export complete coupling distribution for this occupancy to CSV")
    args = ap.parse_args(argv)
    try:
        r, c, o, a = args.r, args.c, args.o, args.a
        if r <= 0 or c <= 0:
            raise MRCDataError("r and c must both be positive")
        if not 0 <= o <= r * c:
            raise MRCDataError(f"Occupancy o must be in [0,{r*c}]")
        if not 0 <= a <= 2 * r * c - r - c:
            raise MRCDataError(f"Coupling a must be in [0,{2*r*c-r-c}]")
        if not 3 <= args.precision <= 60:
            raise MRCDataError("--precision must be between 3 and 60")
        source = locate_csv(args.data_dir.expanduser(), r, c)
        counts = read_occupancy(source, r, c, o)
        result = calculate_statistics(r, c, o, a, counts, args.precision)
        result["source"] = str(source)
        if args.export_csv:
            write_distribution(args.export_csv.expanduser(), r, c, o, counts, args.precision)
            result["export_csv"] = str(args.export_csv)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_output(result, source))
            if args.export_csv:
                print(f"Distribution exported to: {args.export_csv}")
        return 0
    except MRCDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
