#!/usr/bin/env python3
"""Exact null-model statistics for m(r,c,o,a), read from mrc-data CSV tables.

Requires Python 3.9+; no third-party dependencies. This does NOT generate MRC counts.
The null model uniformly selects o occupied cells from an r x c rectangle.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
import csv
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from math import comb
import json
import os
from pathlib import Path
import sys
from typing import Dict, Optional, Iterable


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


def read_occupancies(path: Path, r: int, c: int,
                     occupancies: Iterable[int]) -> Dict[int, Dict[int, int]]:
    """Read several occupancies in ONE scan of the table, checking .DONE.

    Only requested occupancies are retained; all records are checked for
    well-formedness, legal counts, and dimensions. Sparse and dense accepted.
    """
    requested = set(occupancies)
    n = r * c
    if any(not 0 <= o <= n for o in requested):
        raise MRCDataError(f"Requested occupancy outside [0,{n}]")
    counts = {o: {} for o in requested}
    dims = {(r, c), (c, r)}
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
                if oo in requested:
                    if aa in counts[oo]:
                        raise MRCDataError(
                            f"Duplicate occupancy/coupling entry ({oo},{aa}) in {path}"
                        )
                    counts[oo][aa] = count
    except OSError as exc:
        raise MRCDataError(f"Could not read {path}: {exc}") from exc
    if not done:
        raise MRCDataError(f"No terminal .DONE. sentinel in {path}; file may be incomplete")
    for o in requested:
        if not counts[o]:
            raise MRCDataError(f"No records for occupancy o={o} in {path}")
        actual = sum(counts[o].values())
        expected = comb(n, o)
        if actual != expected:
            raise MRCDataError(
                f"Normalization FAILED at occupancy {o} in {path}: "
                f"sum_a m={actual}, expected C({n},{o})={expected}"
            )
    return counts


def read_occupancy(path: Path, r: int, c: int, o: int) -> Dict[int, int]:
    """Compatibility wrapper for one occupancy."""
    return read_occupancies(path, r, c, [o])[o]


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


@dataclass
class DistributionProfile:
    """Validated occupancy distribution, reusable for any observed coupling a."""
    r: int
    c: int
    o: int
    counts: Dict[int, int]
    total: int
    support: list
    cumulative: list
    sorted_masses: list
    mass_cumulative: list
    amin: int
    amax: int
    mean: Fraction
    variance: Fraction
    modes: list
    quantiles: dict
    formatted_by_precision: dict


def prepare_distribution(r: int, c: int, o: int,
                         countmap: Dict[int, int]) -> DistributionProfile:
    """Validate once, then answer many a queries using binary searches."""
    n = r * c
    if r <= 0 or c <= 0 or not 0 <= o <= n:
        raise MRCDataError("Invalid dimensions or occupancy")
    edges = 2 * n - r - c
    if any(not 0 <= k <= edges or v < 0 for k, v in countmap.items()):
        raise MRCDataError("Invalid coupling index or count in distribution")
    total = comb(n, o)
    if sum(countmap.values()) != total:
        raise MRCDataError("Occupancy distribution is not normalized")
    support = sorted(k for k, v in countmap.items() if v > 0)
    if not support:
        raise MRCDataError("No attainable coupling counts for this occupancy")
    amin, amax = support[0], support[-1]
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
    cumulative = [0]
    for k in support:
        cumulative.append(cumulative[-1] + countmap[k])
    sorted_masses = sorted(countmap[k] for k in support)
    mass_cumulative = [0]
    for w in sorted_masses:
        mass_cumulative.append(mass_cumulative[-1] + w)
    mode_height = max(countmap.values())
    modes = [k for k in support if countmap[k] == mode_height]
    q_specs = [("q025", "0.025"), ("q05", "0.05"),
               ("q25", "0.25"), ("median", "0.5"),
               ("q75", "0.75"), ("q95", "0.95"),
               ("q975", "0.975")]
    quantiles = {name: quantile(support, countmap, total, Fraction(p))
                 for name, p in q_specs}
    return DistributionProfile(
        r, c, o, countmap, total, support, cumulative,
        sorted_masses, mass_cumulative, amin, amax, mean, variance,
        modes, quantiles, {}
    )


def statistics_from_profile(profile: DistributionProfile, a: int,
                            precision: int = 16) -> dict:
    """Run a coupling query against a prepared profile (no linear rescans)."""
    r, c, o = profile.r, profile.c, profile.o
    n = r * c
    edges = 2 * n - r - c
    if not 0 <= a <= edges:
        raise MRCDataError(f"Coupling a must be in [0,{edges}]")
    total = profile.total
    countmap = profile.counts
    mean, variance = profile.mean, profile.variance
    amin, amax = profile.amin, profile.amax
    if precision not in profile.formatted_by_precision:
        profile.formatted_by_precision[precision] = {
            "n_cells": n,
            "possible_edges": edges,
            "occupancy_fraction": decimal_value(Fraction(o, n), precision),
            "total_placements": str(total),
            "amin": amin, "amax": amax,
            "support_size": len(profile.support),
            "mean": decimal_value(mean, precision),
            "mean_exact": rational_json(mean),
            "variance": decimal_value(variance, precision),
            "variance_exact": rational_json(variance),
            "stddev": decimal_sqrt(variance, precision),
            "z_min": z_decimal(Fraction(amin) - mean, variance, precision) if variance > 0 else None,
            "z_max": z_decimal(Fraction(amax) - mean, variance, precision) if variance > 0 else None,
            "mode": profile.modes,
            "quantiles": profile.quantiles,
        }
    shared = profile.formatted_by_precision[precision]
    mass = countmap.get(a, 0)
    less = profile.cumulative[bisect_left(profile.support, a)]
    greater = total - less - mass
    fractions = {
        "pmf": Fraction(mass, total),
        "cdf_le": Fraction(less + mass, total),
        "tail_ge": Fraction(greater + mass, total),
        "tail_lt": Fraction(less, total),
        "tail_gt": Fraction(greater, total),
        "midrank_percentile": Fraction(2 * less + mass, 2 * total),
    }
    # Exact two-sided tail defined by distance from the null mean.
    distance = abs(Fraction(a) - mean)
    if distance == 0:
        distance_count = total
    else:
        left = profile.cumulative[bisect_right(profile.support, mean - distance)]
        right = total - profile.cumulative[bisect_left(profile.support, mean + distance)]
        distance_count = left + right
    fractions["two_sided_distance_p"] = Fraction(distance_count, total)
    # Exact discrete two-sided alternative: probability (mass) ordering.
    mass_count = profile.mass_cumulative[bisect_right(profile.sorted_masses, mass)]
    fractions["two_sided_probability_order_p"] = Fraction(mass_count, total)

    attainable = mass > 0
    span = amax - amin
    bounded = Fraction(a - amin, span) if attainable and span else None
    centered = None
    if attainable and variance > 0:
        if Fraction(a) >= mean:
            centered = (Fraction(a) - mean) / (Fraction(amax) - mean)
        else:
            centered = (Fraction(a) - mean) / (mean - Fraction(amin))
    z_score = z_decimal(Fraction(a) - mean, variance, precision) if variance > 0 else None

    result = {
        "r": r, "c": c, "o": o, "a": a,
        **shared,
        "count": str(mass), "attainable": attainable,
        "z_score": z_score,
        "bounded_aggregation": decimal_value(bounded, precision) if bounded is not None else None,
        "bounded_centered_deviation": decimal_value(centered, precision) if centered is not None else None,
        "probabilities": {
            name: {"decimal": decimal_value(fr, precision), "exact": rational_json(fr)}
            for name, fr in fractions.items()
        },
    }
    return result


def calculate_statistics(r: int, c: int, o: int, a: int,
                         countmap: Dict[int, int], precision: int = 16) -> dict:
    """Compatibility API for single queries; batch mode prepares only once."""
    return statistics_from_profile(prepare_distribution(r, c, o, countmap), a, precision)


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


# Output columns are prefixed to avoid overwriting user sample identifiers.
BATCH_STATS_COLUMNS = [
    "mrc_status", "mrc_error", "mrc_source", "mrc_count",
    "mrc_total_placements", "mrc_attainable", "mrc_occupancy_fraction",
    "mrc_possible_edges", "mrc_amin", "mrc_amax", "mrc_support_size",
    "mrc_mean", "mrc_variance", "mrc_stddev", "mrc_z_score",
    "mrc_z_min", "mrc_z_max", "mrc_bounded_aggregation",
    "mrc_bounded_centered_deviation", "mrc_midrank_percentile",
    "mrc_midrank_percentile_fraction", "mrc_pmf", "mrc_pmf_fraction",
    "mrc_cdf_le", "mrc_cdf_le_fraction",
    "mrc_tail_ge", "mrc_tail_ge_fraction",
    "mrc_tail_lt", "mrc_tail_gt",
    "mrc_two_sided_distance_p", "mrc_two_sided_distance_p_fraction",
    "mrc_two_sided_probability_order_p",
    "mrc_two_sided_probability_order_p_fraction",
    "mrc_modes", "mrc_q025", "mrc_q05", "mrc_q25",
    "mrc_median", "mrc_q75", "mrc_q95", "mrc_q975",
]


def _fraction_text(exact: dict) -> str:
    return f"{exact['numerator']}/{exact['denominator']}"


def _batch_result(stats: dict, source: Path) -> dict:
    """Flatten a single report for CSV output without rounding exact fractions."""
    row = {
        "mrc_status": "ok", "mrc_error": "", "mrc_source": str(source),
        "mrc_count": stats["count"],
        "mrc_total_placements": stats["total_placements"],
        "mrc_attainable": str(stats["attainable"]).lower(),
        "mrc_occupancy_fraction": stats["occupancy_fraction"],
        "mrc_possible_edges": stats["possible_edges"],
        "mrc_amin": stats["amin"], "mrc_amax": stats["amax"],
        "mrc_support_size": stats["support_size"],
        "mrc_mean": stats["mean"],
        "mrc_variance": stats["variance"],
        "mrc_stddev": stats["stddev"],
        "mrc_z_score": stats["z_score"],
        "mrc_z_min": stats["z_min"], "mrc_z_max": stats["z_max"],
        "mrc_bounded_aggregation": stats["bounded_aggregation"],
        "mrc_bounded_centered_deviation": stats["bounded_centered_deviation"],
        "mrc_modes": ";".join(str(v) for v in stats["mode"]),
    }
    for key, value in stats["quantiles"].items():
        row["mrc_" + key] = value
    for name, data in stats["probabilities"].items():
        row["mrc_" + name] = data["decimal"]
        fraction_col = "mrc_" + name + "_fraction"
        if fraction_col in BATCH_STATS_COLUMNS:
            row[fraction_col] = _fraction_text(data["exact"])
    return row


def _valid_batch_request(row: dict, line_num: int) -> tuple:
    if None in row or any(value is None for value in row.values()):
        raise MRCDataError(f"Malformed CSV record on line {line_num}")
    try:
        r, c, o, a = (int(row[key].strip()) for key in ("r", "c", "o", "a"))
    except (ValueError, AttributeError) as exc:
        raise MRCDataError(f"Expected integer r,c,o,a on line {line_num}") from exc
    if r <= 0 or c <= 0:
        raise MRCDataError("r and c must both be positive")
    if not 0 <= o <= r * c:
        raise MRCDataError(f"Occupancy o must be in [0,{r*c}]")
    edges = 2 * r * c - r - c
    if not 0 <= a <= edges:
        raise MRCDataError(f"Coupling a must be in [0,{edges}]")
    return r, c, o, a


def run_batch(batch_input: Path, output: Path, data_dir: Path,
              precision: int = 16) -> tuple:
    """Analyze an observation CSV, returning (successful, failed).

    One scan per distinct rectangular shape, even when many occupancies are
    requested. One validated statistical profile per (shape, occupancy).
    Produces one output record per input record in original order.
    """
    if batch_input.resolve() == output.resolve():
        raise MRCDataError("Batch input and output files must be different")
    try:
        with batch_input.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise MRCDataError("Batch input has no CSV header")
            fields = [name.strip() for name in reader.fieldnames]
            if len(set(fields)) != len(fields) or any(not name for name in fields):
                raise MRCDataError("Batch input has duplicate or blank column names")
            required = {"r", "c", "o", "a"}
            if not required.issubset(fields):
                raise MRCDataError(
                    "Batch input must contain columns r,c,o,a (other columns are allowed)"
                )
            collisions = sorted(set(fields) & set(BATCH_STATS_COLUMNS))
            if collisions:
                raise MRCDataError(
                    "Input columns conflict with calculated columns: " + ", ".join(collisions)
                )
            # DictReader uses its original names; accept whitespace around headers.
            reader.fieldnames = fields
            rows = []
            groups = {}
            additions = []
            for line_num, record in enumerate(reader, start=2):
                idx = len(rows)
                rows.append(record)
                additions.append({})
                try:
                    r, c, o, a = _valid_batch_request(record, line_num)
                except MRCDataError as exc:
                    additions[idx] = {"mrc_status": "error", "mrc_error": str(exc)}
                    continue
                shape = (min(r, c), max(r, c))
                groups.setdefault(shape, {}).setdefault(o, []).append((idx, a))
    except OSError as exc:
        raise MRCDataError(f"Unable to read batch input {batch_input}: {exc}") from exc

    scans = 0
    for (r, c), by_o in groups.items():
        try:
            source = locate_csv(data_dir, r, c)
            tables = read_occupancies(source, r, c, by_o)
            scans += 1
            for o, observations in by_o.items():
                profile = prepare_distribution(r, c, o, tables[o])
                for idx, a in observations:
                    stats = statistics_from_profile(profile, a, precision)
                    additions[idx] = _batch_result(stats, source)
        except MRCDataError as exc:
            # Missing/incomplete/corrupt table: mark affected rows, never
            # silently fall back to approximate statistics or extrapolation.
            for observations in by_o.values():
                for idx, _ in observations:
                    additions[idx] = {"mrc_status": "error", "mrc_error": str(exc)}

    successes = sum(add.get("mrc_status") == "ok" for add in additions)
    failures = len(additions) - successes
    try:
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields + BATCH_STATS_COLUMNS,
                                    extrasaction="raise")
            writer.writeheader()
            for original, computed in zip(rows, additions):
                writer.writerow({**original, **computed})
    except OSError as exc:
        raise MRCDataError(f"Unable to write batch output {output}: {exc}") from exc
    return successes, failures, scans


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
    ap.add_argument("r", nargs="?", type=int, help="Grid rows (single-query mode)")
    ap.add_argument("c", nargs="?", type=int, help="Grid columns (single-query mode)")
    ap.add_argument("o", nargs="?", type=int, help="Number of occupied cells (single-query mode)")
    ap.add_argument("a", nargs="?", type=int, help="Observed couplings (single-query mode)")
    ap.add_argument("--batch", type=Path, metavar="INPUT.csv",
                    help="Batch mode: CSV observations with columns r,c,o,a")
    ap.add_argument("--output", type=Path, metavar="RESULTS.csv",
                    help="Batch mode: output CSV with per-observation statistics")
    ap.add_argument("--data-dir", type=Path, default=guess_data_dir(),
                    help="Directory containing R.C.csv; default: MRC_DATA_DIR, ./data, or ~/dev/mrc-data/data")
    ap.add_argument("--precision", type=int, default=16,
                    help="Significant decimal digits shown (default 16)")
    ap.add_argument("--json", action="store_true", help="Single mode: JSON with exact rational probabilities")
    ap.add_argument("--export-csv", type=Path, metavar="FILE",
                    help="Single mode: export complete coupling distribution to CSV")
    args = ap.parse_args(argv)
    try:
        if not 3 <= args.precision <= 60:
            raise MRCDataError("--precision must be between 3 and 60")
        if args.batch is not None:
            if any(v is not None for v in (args.r, args.c, args.o, args.a)):
                raise MRCDataError("Do not supply positional r,c,o,a in --batch mode")
            if args.output is None:
                raise MRCDataError("--output RESULTS.csv is required with --batch")
            if args.json or args.export_csv is not None:
                raise MRCDataError("--json and --export-csv apply only to single-query mode")
            good, bad, scans = run_batch(
                args.batch.expanduser(), args.output.expanduser(),
                args.data_dir.expanduser(), args.precision
            )
            print(f"Batch complete: {good} successful, {bad} errors, "
                  f"{scans} completed source-table scans; output: {args.output}",
                  file=sys.stderr)
            return 1 if bad else 0
        if args.output is not None:
            raise MRCDataError("--output may only be used with --batch")
        if any(v is None for v in (args.r, args.c, args.o, args.a)):
            raise MRCDataError("Single-query mode requires r c o a (or use --batch)")
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
