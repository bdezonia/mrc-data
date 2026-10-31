#!/usr/bin/env python3
"""Independent exact-integer audit of mrc-data r.c.csv files.

It does not import the MRC statistics calculator or the butterfly generator.
Checks normalization, 1st/2nd/3rd binomial coupling moments, several exact
boundary rows, terminal .DONE. marker, and schema. Optional independent
brute-force enumeration and modular naive transfer fingerprints.

Python >= 3.9, standard library only.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from math import comb
from pathlib import Path
import re
import sys
from typing import Dict, Tuple

FILE_NAME = re.compile(r"^(\d+)\.(\d+)\.csv$")
HEADER = ["r", "c", "o", "a", "count"]
# Both primes; fixed points make the audit deterministic and reproducible.
PROBES = ((1_000_000_007, 31, 47), (1_000_000_009, 53, 71))


class AuditError(ValueError):
    pass


def binom(n: int, k: int) -> int:
    """Combinatorial binomial with value zero for impossible arguments."""
    return comb(n, k) if 0 <= k <= n else 0


def edges_and_degrees(r: int, c: int):
    """Build nearest-neighbor graph independently from row-mask machinery."""
    degrees = [0] * (r * c)
    edges = []
    for i in range(r):
        for j in range(c):
            u = i * c + j
            if j + 1 < c:
                v = u + 1
                edges.append((u, v))
                degrees[u] += 1
                degrees[v] += 1
            if i + 1 < r:
                v = u + c
                edges.append((u, v))
                degrees[u] += 1
                degrees[v] += 1
    return edges, degrees


def pair_triple_edge_counts(r: int, c: int):
    """Combinatorial counts of 2-/3-edge subsets by covered vertices.

    A rectangle's graph has no triangles.
    S: unordered edge pairs covering 3 vertices (sharing an endpoint).
    C4: three-edge sets covering 4 vertices (a 3-star or 3-edge path).
    C5: three-edge sets covering 5 vertices.
    C6: three-edge sets covering 6 vertices.
    """
    edges, degrees = edges_and_degrees(r, c)
    e = len(edges)
    shared = sum(binom(d, 2) for d in degrees)
    paths = sum((degrees[u] - 1) * (degrees[v] - 1) for u, v in edges)
    stars = sum(binom(d, 3) for d in degrees)
    c4 = paths + stars
    c5 = shared * (e - 2) - 2 * paths - 3 * stars if e >= 3 else 0
    c6 = binom(e, 3) - c4 - c5
    if min(c4, c5, c6) < 0:
        raise AssertionError("Error deriving edge-triple classes")
    if c4 + c5 + c6 != binom(e, 3):
        raise AssertionError("Edge-triple classes do not partition all triples")
    return e, shared, binom(e, 2) - shared, c4, c5, c6, degrees


def expected_moments(r: int, c: int, o: int, graph_info=None):
    """Exact sums of C(A,k) over all configurations, k=0,1,2,3."""
    n = r * c
    if graph_info is None:
        graph_info = pair_triple_edge_counts(r, c)
    e, shared, disjoint, c4, c5, c6, _ = graph_info
    return (
        binom(n, o),
        e * binom(n - 2, o - 2),
        shared * binom(n - 3, o - 3) + disjoint * binom(n - 4, o - 4),
        c4 * binom(n - 4, o - 4)
        + c5 * binom(n - 5, o - 5)
        + c6 * binom(n - 6, o - 6),
    )


def expected_edge_case_rows(r: int, c: int, graph_info=None):
    """Exact low-occupancy and high-occupancy distributions."""
    if graph_info is None:
        graph_info = pair_triple_edge_counts(r, c)
    n = r * c
    e, shared, _, _, _, _, degrees = graph_info
    rows = {0: {0: 1}}
    if n >= 1:
        rows[1] = {0: n}
    if n >= 2:
        rows[2] = {0: binom(n, 2) - e, 1: e}
    if n >= 3:
        # Grid graphs are triangle-free, so 3 occupied vertices induce <=2 edges.
        k2 = shared
        k1 = e * (n - 2) - 2 * k2
        rows[3] = {0: binom(n, 3) - k1 - k2, 1: k1, 2: k2}
    rows[n] = {e: 1}
    vacancy = {}
    for degree in degrees:
        a = e - degree
        vacancy[a] = vacancy.get(a, 0) + 1
    rows[n - 1] = vacancy
    return rows


def brute_counts(r: int, c: int):
    """Independent exhaustive enumeration, for n small only."""
    n = r * c
    edge_masks = [(1 << u) | (1 << v) for u, v in edges_and_degrees(r, c)[0]]
    result: Dict[Tuple[int, int], int] = {}
    for mask in range(1 << n):
        o = mask.bit_count()
        a = sum((mask & em) == em for em in edge_masks)
        key = (o, a)
        result[key] = result.get(key, 0) + 1
    return result


def naive_transfer_evaluation(r: int, c: int, x: int, y: int, prime: int):
    """Evaluate G(x,y) mod p with direct O(height*4^width) transitions.

    Deliberately does NOT use the butterfly factorization or coefficients.
    """
    width, height = min(r, c), max(r, c)
    size = 1 << width
    xy = [pow(x, m.bit_count(), prime) * pow(y, (m & (m << 1)).bit_count(), prime) % prime
          for m in range(size)]
    ypowers = [pow(y, k, prime) for k in range(width + 1)]
    f = xy[:]
    for _ in range(1, height):
        nxt = [0] * size
        for m in range(size):
            s = 0
            for previous, old in enumerate(f):
                s += old * ypowers[(m & previous).bit_count()]
            nxt[m] = xy[m] * (s % prime) % prime
        f = nxt
    return sum(f) % prime


def hash_file(path: Path):
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class AuditResult:
    file: str
    r: int
    c: int
    records: int
    nonzero_records: int
    max_occupied: int
    max_couplings: int
    moment_checks: str
    boundary_checks: str
    brute_force: str
    fingerprints: str
    sha256: str
    status: str
    error: str


def audit_file(path: Path, brute_cells: int = 16, transfer_width: int = 6):
    match = FILE_NAME.fullmatch(path.name)
    if not match:
        raise AuditError(f"Unexpected CSV filename: {path.name}")
    r, c = map(int, match.groups())
    if not r or not c:
        raise AuditError(f"Nonpositive dimensions in {path.name}")
    graph = pair_triple_edge_counts(r, c)
    n, e = r * c, graph[0]
    expected_edges = 2 * n - r - c
    if e != expected_edges:
        raise AssertionError("Graph edge count disagreement")
    actual = [[0] * (n + 1) for _ in range(4)]
    special = expected_edge_case_rows(r, c, graph)
    observed_special = {o: {} for o in special}
    seen_keys = set()
    stored = {} if n <= brute_cells else None
    mod_expected = [0] * len(PROBES) if min(r, c) <= transfer_width else None
    xpows = []
    ypows = []
    if mod_expected is not None:
        for prime, x, y in PROBES:
            xpows.append([pow(x, i, prime) for i in range(n + 1)])
            ypows.append([pow(y, i, prime) for i in range(e + 1)])
    done = False
    records = 0
    nonzero = 0
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            try:
                header = [s.strip() for s in next(reader)]
            except StopIteration:
                raise AuditError("Empty file")
            if header != HEADER:
                raise AuditError(f"Bad header {header!r}; expected {HEADER!r}")
            for linenum, row in enumerate(reader, 2):
                if not row or all(not cell.strip() for cell in row):
                    continue
                if row == [".DONE."]:
                    done = True
                    for remaining in reader:
                        if remaining and any(s.strip() for s in remaining):
                            raise AuditError("Nonblank data after .DONE.")
                    break
                if len(row) != 5:
                    raise AuditError(f"Line {linenum}: expected five columns, got {row!r}")
                try:
                    rr, cc, o, a, count = (int(s.strip()) for s in row)
                except ValueError as exc:
                    raise AuditError(f"Line {linenum}: noninteger field") from exc
                if (rr, cc) not in ((r, c), (c, r)):
                    raise AuditError(f"Line {linenum}: dimensions {rr}x{cc} differ from file name")
                if not (0 <= o <= n and 0 <= a <= e and count >= 0):
                    raise AuditError(f"Line {linenum}: invalid occupancy/coupling/count")
                key_number = o * (e + 1) + a
                if key_number in seen_keys:
                    raise AuditError(f"Line {linenum}: duplicate (o,a)=({o},{a})")
                seen_keys.add(key_number)
                actual[0][o] += count
                actual[1][o] += a * count
                actual[2][o] += binom(a, 2) * count
                actual[3][o] += binom(a, 3) * count
                if o in observed_special:
                    observed_special[o][a] = count
                if stored is not None and count:
                    stored[(o, a)] = count
                if mod_expected is not None and count:
                    for i, (prime, _, _) in enumerate(PROBES):
                        mod_expected[i] = (mod_expected[i] + count * xpows[i][o] * ypows[i][a]) % prime
                records += 1
                nonzero += count != 0
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AuditError(f"I/O or CSV read failure: {exc}") from exc
    if not done:
        raise AuditError("Missing terminal .DONE. marker")
    if not records:
        raise AuditError("No data rows")
    for o in range(n + 1):
        expected = expected_moments(r, c, o, graph)
        got = tuple(actual[k][o] for k in range(4))
        for k in range(4):
            if got[k] != expected[k]:
                raise AuditError(
                    f"Moment order {k} FAILED for o={o}: got {got[k]}, expected {expected[k]}"
                )
    for o, expected_dist in special.items():
        got = {a: count for a, count in observed_special[o].items() if count}
        expected_dist = {a: count for a, count in expected_dist.items() if count}
        if got != expected_dist:
            raise AuditError(f"Exact boundary row FAILED o={o}: got {got}, expected {expected_dist}")
    brute_status = "not_applicable"
    if stored is not None:
        expected_brute = brute_counts(r, c)
        if stored != expected_brute:
            different = next((k for k in sorted(set(stored) | set(expected_brute))
                              if stored.get(k, 0) != expected_brute.get(k, 0)), None)
            raise AuditError(
                f"Independent brute-force mismatch at {different}: "
                f"CSV={stored.get(different, 0)}, brute={expected_brute.get(different, 0)}"
            )
        brute_status = "PASS"
    fp_status = "not_applicable"
    if mod_expected is not None:
        for i, (prime, x, y) in enumerate(PROBES):
            value = naive_transfer_evaluation(r, c, x, y, prime)
            if value != mod_expected[i]:
                raise AuditError(
                    f"Independent naive-transfer fingerprint {i+1} FAILED: "
                    f"CSV={mod_expected[i]} direct={value} mod {prime}"
                )
        fp_status = "PASS_2_modular_probes"
    return AuditResult(
        str(path), r, c, records, nonzero, n, e, "PASS_0_to_3", "PASS",
        brute_status, fp_status, hash_file(path), "PASS", ""
    )


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, help="Folder containing r.c.csv MRC tables")
    parser.add_argument("--report", type=Path, default=Path("mrc_validation_report.csv"),
                        help="Per-table CSV report (default mrc_validation_report.csv)")
    parser.add_argument("--brute-cells", type=int, default=16,
                        help="Use independent full brute force when rc <= N (default 16; 0 disables)")
    parser.add_argument("--transfer-width", type=int, default=6,
                        help="Two independent direct-transfer modular checks when min(r,c) <= N (default 6; 0 disables)")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)
    if args.brute_cells < 0 or args.transfer_width < 0:
        parser.error("limits must be nonnegative")
    if args.brute_cells > 23:
        parser.error("--brute-cells over 23 is potentially extremely slow; use <=23")
    if args.transfer_width > 9:
        parser.error("--transfer-width over 9 is extremely slow; use <=9")
    data_dir = args.data_dir.expanduser()
    if not data_dir.is_dir():
        parser.error(f"Not a directory: {data_dir}")
    files = sorted(
        (p for p in data_dir.rglob("*.csv") if FILE_NAME.fullmatch(p.name)),
        key=lambda p: (int(FILE_NAME.fullmatch(p.name)[1]),
                       int(FILE_NAME.fullmatch(p.name)[2]), str(p)),
    )
    if not files:
        parser.error(f"No r.c.csv tables found under {data_dir}")
    results = []
    failed = 0
    for index, path in enumerate(files, 1):
        try:
            result = audit_file(path, args.brute_cells, args.transfer_width)
            print(f"[{index}/{len(files)}] PASS {path.name} "
                  f"moments=0..3 brute={result.brute_force} transfer={result.fingerprints}", flush=True)
        except (AuditError, AssertionError) as exc:
            failed += 1
            match = FILE_NAME.fullmatch(path.name)
            r, c = map(int, match.groups())
            result = AuditResult(str(path), r, c, 0, 0, r*c, 2*r*c-r-c,
                                 "", "", "", "", "", "FAIL", str(exc))
            print(f"[{index}/{len(files)}] FAIL {path.name}: {exc}", file=sys.stderr, flush=True)
        results.append(result)
        if failed and args.fail_fast:
            break
    report = args.report.expanduser()
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(AuditResult.__dataclass_fields__))
        writer.writeheader()
        for result in results:
            writer.writerow(vars(result))
    print(f"\nChecked {len(results)} tables: {len(results)-failed} PASS, "
          f"{failed} FAIL. Report: {report}")
    print("IMPORTANT: This is computational validation, not a formal proof that the")
    print("published CSV coefficients equal the mathematically defined m(r,c,o,a).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
