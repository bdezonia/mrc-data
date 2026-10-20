# MRC Fast Butterfly v2: occupancy-banded coupling storage

**Separate, experimental upgrade** to the original MRC fast butterfly generator.
Do not install over an active batch run; finish or stop the old batch first.
This package lives in its own `mrc_fast_kernel/` folder and has identical
`mrc_fast_generate.py` CSV output and `.DONE` marker conventions.

## Main difference

The previous C++ kernel allocated a full rectangular `(o,a)` coefficient array
for each last-row mask. The v2 kernel stores only the exact conservative band

    max(0, E-4*(N-o)) <= a <= min(E, 2*o)

for each occupancy `o`, where `N` and `E` count cells and edges in the processed
partial grid. During butterfly transformations the upper band has `width` units
of temporary space for extra `y` factors. The band uses a separate offset for
every `o`. No approximation is used; CRT still reconstructs exact integers.

## Build and test

    cd mrc_fast_kernel
    bash build.sh
    python3 test_mrc_fast_generate.py
    python3 mrc_estimate.py --r 15 --c 40

Test a modest archived rectangle independently:

    python3 mrc_fast_generate.py --r 10 --c 12 --out /tmp/10.12.csv \\
      --memory-gb 4

## Starting a fresh unattended batch

Stop the original batch before restarting it with this code; the two batch
runners use the same directory lock and output conventions. Do NOT launch
both simultaneously against the same output directory. The new batch script
skips `r.c.DONE` files and uses the same per-prime CRT cache format.

    python3 mrc_batch_generate.py --r-min 1 --r-max 24 --c-max 40 \\
      --out-dir ~/dev/mrc-data/data --memory-gb 64

Or use `run_mrc_full_batch.sh` in the same way as the prior release.

**Do not replace the old executable while it is in use.** Compile this ZIP
in a different directory first. If you prefer, keep the old installation
entirely unchanged and run this one after it finishes.

## Capacity estimates: C++ coefficient arrays only

                 old dense    new v2 ragged
    13 x 13       3.07 GiB        0.99 GiB
    14 x 29      37.29 GiB       11.06 GiB
    14 x 40      71.72 GiB       20.88 GiB
    15 x 29      85.80 GiB       25.29 GiB
    15 x 40     165.05 GiB       47.75 GiB
    16 x 16      57.60 GiB       17.82 GiB
    16 x 29     195.62 GiB       57.35 GiB

The estimates are derived from the exact allocated array shapes; runtime
memory may be a bit higher. The `--memory-gb` option limits those two arrays,
NOT the memory used by the Python CRT reconstruction or the OS. Ensure the
OS has sufficient free RAM and choose a conservative limit.

The width-of-bitmask limit remains <24; even widths below 24 may exceed memory.

## Measured single-prime benchmark (test container, not your Xeon)

    rectangle  dense seconds  ragged seconds   dense RSS    ragged RSS
    9x12         0.94            0.39          79.9 MiB     28.1 MiB
    10x12        2.26            1.46         196.2 MiB     66.9 MiB
    11x13        7.58            3.58         560.3 MiB    185.1 MiB
    12x12       14.77            8.88           1.10 GiB   373.4 MiB

Independent correctness checks: old dense kernel byte-identical modular files
for a range of small rectangles, and 12x12 matches archived coefficient values
modulo 2147483647 for all 38,425 table entries; 10x12 CRT exact CSV matches the
existing archive byte-for-byte. These checks do not predict big-grid wall time.

`mrc_fast_transform_dense_reference.cpp` is provided solely to reproduce
comparisons. `build.sh` compiles the ragged version as `mrc_fast_transform`.
