#!/usr/bin/env python3
"""Exact m(r,c,o,a) CSV generator using modular mask-butterfly + CRT.

Python 3.10+. No third-party requirements. Compile C++ with build.sh first.
"""
import argparse
from array import array
import csv
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time


def is_prime_31(n):
    """Deterministic Miller-Rabin for 0 <= n < 2^31 (bases 2,7,61)."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17):
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while not d & 1:
        s += 1
        d //= 2
    for a in (2, 7, 61):
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def exact_primes(total_cells):
    """Enough 31-bit primes to ensure product > 2**(r*c), a strict bound."""
    acc = 1
    prime = 2**31 - 1
    out = []
    while acc <= (1 << total_cells):
        while not is_prime_31(prime):
            prime -= 2
        out.append(prime)
        acc *= prime
        prime -= 2
    return out


def read_mod(path, r, c, p):
    expected_o = r * c
    expected_a = 2 * r * c - r - c
    with open(path, "rb") as fh:
        header = fh.read(28)
        if len(header) != 28:
            raise ValueError("truncated modular header")
        magic, rr, cc, pp, oo, aa = struct.unpack("<8sIIIII", header)
        if (magic, rr, cc, pp, oo, aa) != (b"MRCMOD01", r, c, p, expected_o, expected_a):
            raise ValueError(f"modular header does not match {r=} {c=} {p=}: {(magic, rr, cc, pp, oo, aa)}")
        n = (oo + 1) * (aa + 1)
        data = array("I")
        data.fromfile(fh, n)
        if data.itemsize != 4:
            raise ValueError("requires 32-bit unsigned int platform")
        if sys.byteorder != "little":
            data.byteswap()
        if fh.read(1):
            raise ValueError("trailing data in modular result")
    return data


def generate(r, c, out, kernel, algorithm, memory_gb, verbose, keep_mod, cache_dir=None):
    r, c = sorted((r, c))
    if r < 1:
        raise ValueError("r and c must be positive")
    primes = exact_primes(r * c)
    print(f"rectangle={r}x{c}, cells={r*c}, primes={len(primes)}, width_masks={1<<r}", flush=True)
    combined = None
    modulus_product = 1
    begin = time.perf_counter()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
    # Write to a temporary CSV and atomically replace target only on success.
    with tempfile.TemporaryDirectory(prefix="mrc_mod_", dir=str(out.parent)) as tempdir:
        for idx, p in enumerate(primes, 1):
            mod_file = Path(tempdir) / f"{r}.{c}.{p}.mod"
            cached = cache_dir / mod_file.name if cache_dir is not None else None
            t0 = time.perf_counter()
            if cached is not None and cached.exists():
                try:
                    residues = read_mod(cached, r, c, p)
                    print(f"reusing validated cached prime {p}", flush=True)
                except (ValueError, EOFError, OSError) as e:
                    print(f"cache invalid for {p} ({e}); recomputing", flush=True)
                    cached.unlink(missing_ok=True)
                    residues = None
            else:
                residues = None
            if residues is None:
                cmd = [str(kernel), "--r", str(r), "--c", str(c), "--mod", str(p),
                       "--out", str(mod_file), "--algorithm", algorithm,
                       "--memory-gb", str(memory_gb)]
                if verbose:
                    cmd.append("--verbose")
                subprocess.run(cmd, check=True)
                residues = read_mod(mod_file, r, c, p)
                if cached is not None:
                    os.replace(mod_file, cached)
            if combined is None:
                combined = list(residues)
            else:
                inv = pow(modulus_product % p, -1, p)
                for k, value in enumerate(residues):
                    combined[k] += modulus_product * (((int(value) - combined[k]) % p) * inv % p)
            modulus_product *= p
            print(f"prime {idx}/{len(primes)} p={p} elapsed={time.perf_counter()-t0:.2f}s", flush=True)
            if cached is None:
                if keep_mod:
                    target = out.with_suffix(f".{p}.mod")
                    os.replace(mod_file, target)
                else:
                    mod_file.unlink()
        assert modulus_product > (1 << (r*c))
        # Fundamental validation identity: every configuration counted once.
        # A second independent identity checks o marginals are binomial(n,o).
        amax = 2*r*c - r-c
        for o in range(r*c+1):
            marginal = sum(combined[o*(amax+1):(o+1)*(amax+1)])
            expected = math.comb(r*c, o)
            if marginal != expected:
                raise AssertionError(f"occupancy marginal FAIL at o={o}: {marginal} != {expected}")
        print("validation: all occupancy marginals = binomial(r*c,o) PASS", flush=True)
        tmp_csv = Path(tempdir) / "result.csv"
        with open(tmp_csv, "w", newline="") as file:
            wr = csv.writer(file, lineterminator="\n")
            wr.writerow(("r", "c", "o", "a", "count"))
            for o in range(r*c+1):
                for a in range(amax+1):
                    wr.writerow((r,c,o,a,combined[o*(amax+1)+a]))
            file.write(".DONE.\n")
        os.replace(tmp_csv,out)
    print(f"EXACT {out} entries={len(combined)} total_s={time.perf_counter()-begin:.2f}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--r", type=int, required=True)
    ap.add_argument("--c", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kernel", type=Path, default=Path(__file__).resolve().parent / "mrc_fast_transform")
    ap.add_argument("--algorithm", choices=("butterfly","naive"), default="butterfly",
                    help="naive is ONLY a comparison/reference implementation")
    ap.add_argument("--memory-gb", type=float, default=16.0, help="maximum two-layer RAM in C++ kernel")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--keep-mod", action="store_true", help="save primes beside output (without resume)")
    ap.add_argument("--cache-dir", type=Path, default=None,
                    help="resume completed modular passes after interruption; recommended for large rectangles")
    args=ap.parse_args()
    generate(args.r,args.c,args.out,args.kernel.resolve(),args.algorithm,args.memory_gb,args.verbose,args.keep_mod,args.cache_dir)


if __name__=="__main__":
    main()
