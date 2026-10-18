# Faster exact generation of m(r,c,o,a) — experimental butterfly DP

## What is new?

This is a **new exact enumerator** for all occupancy counts `o` and all nearest-neighbor occupied-pair counts `a` on a rectangle `r×c`. It does **not** depend on archived MRC values, interpolation or an empirical formula. It performs DP, but replaces the expensive mask-to-mask summation of the original `DP_optimized.java` with a bitwise polynomial butterfly and replaces sparse Java `BigInteger` dictionaries by compact modular arrays.

Define `F_h(S; x,y)` to count configurations in the first `h` rows whose final row's occupied mask is `S`. A row extension satisfies

    F_{h+1}(T;x,y) = x^{popcount(T)} y^{horiz(T)} Σ_S F_h(S;x,y) y^{popcount(S&T)}.

The expensive sum is a tensor product. Along each mask bit, transform the two input polynomials by

    (f0, f1) -> (f0 + f1, f0 + y*f1).

After all width `w` bits, every output mask `T` has the correctly weighted sum. The bit butterflies cost `O(w·2^w)` polynomial coefficient operations rather than `O(4^w)` for the conventional all-pairs transition; neither estimate includes row count or polynomial dimensions. It is still exponential in **width**. The total coefficient workload and RAM still grow rapidly for larger rectangles.

The compiled kernel counts modulo a 31-bit prime, and the Python wrapper repeats the calculation with enough different primes to guarantee that their product exceeds `2^(r*c)` (an upper bound on any desired count), then reconstructs each exact nonnegative integer by the Chinese remainder theorem. An exact cross-check verifies every occupancy marginal equals `binomial(r*c,o)`.

## Requirements

* Linux with `g++` supporting C++17, Python >= 3.10 (no third-party Python packages).
* RAM proportional to `2^min(r,c) × (rc) × (2rc-r-c)` with two layers of 32-bit integers. Exact peak memory is printed in the verbose log. For larger inputs, select a generous `--memory-gb` guard to avoid accidental over-allocation.
* Disk for output CSV. A separate modular pass is computed for each of roughly `ceil(r*c/31)` primes.

## Quick start

    unzip mrc_fast_butterfly_bundle.zip
    cd mrc_fast_kernel
    ./build.sh
    python3 test_mrc_fast_generate.py
    python3 mrc_fast_generate.py --r 10 --c 12 --out 10.12.csv --verbose --memory-gb 16

For your intended workstation, a cautious first benchmark:

    /usr/bin/time -v python3 mrc_fast_generate.py --r 11 --c 13 --out 11.13.csv --memory-gb 32

Larger experiments, subject to adequate RAM and run-time:

    python3 mrc_estimate.py --r 12 --c 20
    /usr/bin/time -v python3 mrc_fast_generate.py --r 12 --c 20 --out 12.20.csv --memory-gb 80 --cache-dir 12.20.crt_cache

`--cache-dir` is recommended for serious runs: each finished modular-prime pass is saved immediately. Re-running the same command reuses validated passes already on disk, even if the previous run was interrupted. It **does not** checkpoint within a single prime pass; an interrupted prime has to restart. If a run exhausts RAM or takes too long, caching alone does not fix the underlying bottleneck.

`--r`, `--c` are interchangeable; the shorter dimension becomes mask width. The CSV format is `r,c,o,a,count` with a final `.DONE.` sentinel, matching the original generator. Use `--keep-mod` only if intermediate modular outputs are useful for debugging. The output is written atomically: incomplete results cannot masquerade as finished CSV files.

To compare against the conventional (but dense) mask-pair algorithm:

    ./mrc_fast_transform --r 7 --c 9 --mod 2147483647 --out fast.mod --algorithm butterfly
    ./mrc_fast_transform --r 7 --c 9 --mod 2147483647 --out naive.mod --algorithm naive
    cmp fast.mod naive.mod

The `naive` reference mode is for verification only and scales poorly. The Python wrapper also accepts `--algorithm naive`, useful for **small** tables.

## What has been verified?

- Independent exhaustive enumeration through `4×4` (every occupancy and coupling coefficient), including narrow and rectangular edge cases.
- Exact modular agreement with an independent conventional mask-pair implementation on sizes through `7×9`.
- Multi-prime exact CRT agreement on `5×7`.
- Occupancy marginals `Σ_a m(r,c,o,a) = binomial(rc,o)` on all tested full-table runs.
- Complete exact **10×12 CSV byte-for-byte identical** to `../data/10.12.csv` in the October 17 user archive, including zero coefficients and `.DONE.`; all four modular passes plus CRT were finished in approximately 11.5 seconds in the assistant's environment (overall process wall time).
- All 38,425 **12×12** residues matched the original archived integer table modulo 2,147,483,647. This is a modular check, NOT completion of all 12×12 CRT passes.
- Cache/resume tested by repeating exact 5×7 generation and reusing both cached prime passes.

To compare with your `all(2).zip` data (if that ZIP is locally available):

    python3 verify_mrc_archive.py --archive /path/to/all.zip --csv 10.12.csv

Speed measurements made inside the assistant's container (not on the user's Xeon):

| Rectangle | One-prime butterfly runtime | Peak RSS |
|---|---:|---:|
| 7×9 | 0.036 s | 8 MiB |
| 8×10 | 0.158 s | 23 MiB |
| 9×12 | 0.856 s | 80 MiB |
| 10×12 | 2.30 s | 196 MiB |
| 11×13 (unpruned butterfly) | 10.23 s | 560 MiB |
| 12×12 (unpruned butterfly) | 25.22 s | 1130 MiB |
| 12×12 (pruned butterfly) | 13.49 s | 1130 MiB |

The 12×16 and 13×13 runs have **not** been completed here. A partial 12×16 run advanced through 15 rows, but timed out during a tool-limited attempt; extrapolation from smaller grids may fail because large-array memory traffic dominates. The pruning change was benchmarked on 12×12 and validated on smaller grids, but other widths can show different timings. Do not interpret the table as full multi-prime exact CSV runtimes. In particular, this is not yet a demonstration of beating the highly optimized original Java DP on the user's machine, and cannot be claimed without comparative benchmarks.

## Next improvements worth testing

1. Occupancy degree restrictions (`--max-o`, or a bounded `o` interval). This could dramatically reduce the polynomial dimension when the desired occupancy is small, but the present version generates the **full** table.
2. Tighter coupling bounds per occupancy and mask, instead of dense rectangular arrays. This should save RAM and arithmetic, but needs careful indexing.
3. Parallelizing independent modular primes / rows on the Xeon, subject to RAM.
4. GPU modular arithmetic: the butterfly structure maps naturally to CUDA. Benchmarking is needed because low arithmetic intensity and memory transfer can offset GPU gains.
5. A faster alternative based on evaluated generating functions and 2D NTT; likely better for certain density regimes, but not yet implemented.

## Safety limits

`--memory-gb` checks estimated **two-layer** coefficient-array memory before each allocation. Additional memory is used by the final result and Python CRT. No disk checkpoint/resume is implemented (each prime is sequentially completed). The automatically chosen primes are < `2^31`, ensuring every modular sum fits in an unsigned 32-bit integer before subtraction.
