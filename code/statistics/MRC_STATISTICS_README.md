# Exact statistics from `mrc_data`

`mrc_data_statistics.py` reads a **finished** MRC data table and summarizes the distribution of occupied-neighbor couplings for one fixed `(r,c,o)` at an observed `a`. It **does not run enumeration, transfer matrices, or DP**. Requires only Python 3.9+ (no dependencies).

## Run

```bash
python3 mrc_data_statistics.py 6 8 12 14 --data-dir ~/dev/mrc-data/data
```

The four positional arguments are `(r,c,o,a)`:

- `r,c`: grid dimensions (both positive)
- `o`: number of occupied cells in the grid (`0 <= o <= rc`)
- `a`: observed count of occupied orthogonally adjacent cell pairs (`0 <= a <= 2rc-r-c`)

The requested source is `r.c.csv` or, by transposition symmetry, `c.r.csv`. `--data-dir` may be omitted: the script checks `MRC_DATA_DIR`, then `./data`, then a `data` directory next to the script, then `~/dev/mrc-data/data`.

The CSV format is exactly:

```text
r,c,o,a,count
2,2,0,0,1
...
.DONE.
```

The in-file `.DONE.` line must be present. `r.c.DONE` sidecar files are not required; they cannot substitute for the in-file sentinel. Input may be sparse (only nonzero counts) or dense (including zeros). The specified occupancy is validated against the exact total `C(rc,o)` and its exact first **and** second moments. A table that is incomplete or inconsistent is rejected rather than used for scientific statistics.

## Useful commands

```bash
# Read the normal concise report
python3 mrc_data_statistics.py 6 8 12 14 --data-dir ~/dev/mrc-data/data

# Machine-readable output: all exact probabilities include numerator/denominator strings
python3 mrc_data_statistics.py 6 8 12 14 --data-dir ~/dev/mrc-data/data --json > summary.json

# Export ALL coupling values for the chosen occupancy (incl. impossible ones)
python3 mrc_data_statistics.py 6 8 12 14 --data-dir ~/dev/mrc-data/data --export-csv distribution.csv

# Set a different output precision (3 to 60 significant decimal digits)
python3 mrc_data_statistics.py 6 8 12 14 --data-dir ~/dev/mrc-data/data --precision 30

# Test against independent, exhaustively enumerated 1x1, 1x4, 2x2, 2x3, 3x3 grids
python3 -m unittest -v test_mrc_data_statistics.py
```

If your data directory is always the same, you can set:

```bash
export MRC_DATA_DIR=~/dev/mrc-data/data
python3 mrc_data_statistics.py 6 8 12 14
```

## Measures and interpretation

Fix `N=rc` and the observed occupancy `o`. The **null hypothesis** is that all `C(N,o)` placements of occupied cells are equally likely. Let `A` be the number of couplings. The file contains `m(r,c,o,a)`, which is the number of those placements having exactly `a` couplings. The probability is *exactly*

`P(A=a)=m(r,c,o,a)/C(N,o)`.

The report provides:

- Exact counts: `m(r,c,o,a)` and `C(N,o)`.
- The attainable endpoints `amin`, `amax` and number of attainable coupling counts, obtained from nonzero archive counts.
- `P(A=a)`, lower/upper inclusive tails `P(A<=a)` and `P(A>=a)`, and strict tails.
- Midrank percentile `P(A<a)+P(A=a)/2` (a probability in `[0,1]`; multiply by 100 for a percentile in percent). This avoids calling all tied observations the same *upper* percentile.
- Two explicit **exact** two-sided p-value conventions. `distance` is `P(|A-E[A]| >= |a-E[A]|)`; `mass order` is the probability of all possible values whose point mass is <= `P(A=a)`. They can differ because the discrete distribution is skewed or irregular. Neither assumes a normal distribution.
- Exact mean and variance (plus decimal mean, variance, and standard deviation), and the mode(s).
- The smallest coupling values attaining cumulative probabilities of 2.5%, 5%, 25%, 50%, 75%, 95%, 97.5%.
- Ordinary standardized `z=(a-mean)/stddev` and its **attainable** interval `[z(amin),z(amax)]` for this `(r,c,o)`.
- Bounded aggregation score `B=(a-amin)/(amax-amin)`, in `[0,1]` for attainable observations.
- Bounded **mean-centered** deviation: `(a-mean)/(amax-mean)` if `a >= mean`, otherwise `(a-mean)/(mean-amin)`. This equals zero at the null mean and ranges from `-1` at `amin` to `+1` at `amax` when the distribution is nondegenerate. This is **not** a z-score; it is an alternative, bounded scale.

For zero-variance configurations, the z-score and bounded scores are marked `N/A`; the exact probability and quantiles are still defined. For an impossible coupling count (`m=0`), the script reports the zero probability and marks the aggregation indices `N/A`.

The exact moments of the fixed-occupancy null model are checked independently of the CSV counts. If `E=2rc-r-c` is the number of orthogonal grid edges, then

`mean = E * (o)_2/(N)_2`.

Let `S` be the number of unordered pairs of grid edges incident at a common cell. With `p_k=(o)_k/(N)_k`, interpreted as zero when `k>N` or `k>o`,

`E[A²] = E*p2 + 2*S*p3 + 2*(C(E,2)-S)*p4`,

and `variance = E[A²]-mean²`. Both formulas are exact, including for 1D grids.

## Scientific caveats

1. The p-values and percentiles are **exact under the fixed-occupancy, uniform-random-placement null model**. They are not exact p-values for models with environmental constraints, spatial correlation, or nonuniform sampling.
2. A z-score does **not** imply a normal distribution or justify converting `z` to a normal-tail p-value. Use the exact tail probabilities for significance.
3. Bounded aggregation `B` is *geometric position in the attainable coupling range*, not statistical rarity. Its scale is generally nonlinear relative to the cumulative probability.
4. File checks are strong **consistency checks**, not mathematical proof that every archive coefficient is correct. The latter relies on the proven enumeration algorithm and verified implementation. Tests in this ZIP use independent brute-force enumeration on small grids, **not your complete working archive**.
5. A calculation outside available `r.c.csv` tables will fail clearly. No extrapolation is attempted.
6. If the program sees an in-progress file without `.DONE.`, it will fail instead of returning potentially misleading results.
7. `--export-csv` writes *rounded* decimal probabilities. Use `--json` for exact numerator/denominator pairs for the requested `a`.

## Distribution output

`--export-csv` writes rows `r,c,o,a,count,probability,cdf_le,tail_ge` for every integer `a` between `0` and the number of possible grid edges. This is useful for plotting or further analysis. If one only wants exact integer counts, the original table remains authoritative.

## Publication / reproducibility

For a paper or software release, preserve the script, its test suite, the algorithm proof, the generator version, the archive release tag / commit, and cryptographic checksums of the data files. Cite the same archive version that was analyzed. This tool is a **query and statistical-analysis client**, not yet a whole-repository independent validator.
