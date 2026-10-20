# MRC unattended batch runner

This addition uses the **existing** `mrc_fast_generate.py` + C++ butterfly kernel (no new counting algorithm) to generate the 684 rectangular tables `1 <= r <= 24, r <= c <= 40` as far as the current kernel and available resources permit.

## Quick start (Linux, Python 3.10+)

```bash
unzip mrc_fast_batch_runner_2026-10-18.zip
cd mrc_fast_kernel
./build.sh
./run_mrc_full_batch.sh ~/dev/mrc-data/data
```

**To leave it running after closing your terminal:**

```bash
nohup ./run_mrc_full_batch.sh ~/dev/mrc-data/data > ~/mrc_batch_console.log 2>&1 < /dev/null &
echo $!
```

To watch the job:

```bash
tail -f ~/dev/mrc-data/data/mrc_batch.log
```

With no first argument to the shell launcher, data goes to `../data` relative to the `mrc_fast_kernel/` directory (matching the earlier Java generator setup). Alternatively, run `python3 mrc_batch_generate.py --out-dir /your/data/path` from anywhere; the script locates the kernel relative to itself.

## Output files / atomic completion

After each **successfully finished, validated** rectangle, the runner leaves:

```
12.23.csv         # complete original dense CSV with .DONE. line inside
12.23.DONE        # zero bytes, created atomically only after CSV success
```

The two files share an output folder. A missing or nonzero-sized marker is **never** treated as completed. External programs can simply check `12.23.DONE` exists and has zero length; they need not read CSV files.

- Completed jobs with both a zero-byte marker and a nonempty CSV are skipped.
- Existing fully formed dense `r.c.csv` files **without** a marker are inspected (header, final `.DONE.` line, final data row, expected number of rows). A new zero-byte marker is created **without rerunning** the DP. This helps if you point at an existing MRC archive directory. This check does not revalidate every coefficient numerically. Use `--no-recover-existing` if you want all unmarked files regenerated instead.
- In-progress files never get a marker. Underlying generator writes CSV atomically and checks every occupancy marginal equals `binomial(r*c,o)`.
- Interrupted / failed jobs retain any fully completed cached modular-prime passes under `OUT_DIR/.mrc_crt_cache/r.c/`. A rerun reuses those passes. Successful jobs remove their prime cache by default (use `--keep-cache` to retain it).
- `mrc_batch.log` contains timestamped progress and child generator output. `mrc_batch_status.tsv` is a tab-separated per-rectangle status ledger, with timestamps, estimated peak RAM and outcomes. These are appended on every run.
- Simultaneous batch jobs using the same output directory are prevented by a Linux `flock` lock.

## Runtime / resources

The C++ kernel's mask width is `r=min(r,c)`. It currently **refuses width >= 24**. Also, its dense modular layers require very large RAM at widths > 16. The batch runner therefore estimates **two-layer C++ allocation** per rectangle **before** launching it. It defaults to 64 GiB, reserving at least 8 GiB of currently available RAM in addition. This reserve is adjustable, but `--memory-gb` itself controls the kernel allocation guard. Other small allocations and Python CRT memory are additional.

Example peak *two-layer* C++ memory estimates:

| Rectangle | Estimated two-layer peak RAM |
|---|---:|
| 13x13 | 3.07 GiB |
| 13x40 | 30.84 GiB |
| 14x40 | 71.72 GiB |
| 15x15 | 22.10 GiB |
| 16x16 | 57.60 GiB |
| 17x17 | 147.69 GiB |
| 24x40 | 218,940 GiB, and width 24 is not supported |

Out-of-budget rectangles are **recorded as skipped**; the runner continues to other rectangles, rather than risking an out-of-memory crash. This means the requested 684 rectangles are **enumerated**, but not all can be generated with the present algorithm and hardware. Bigger memory limits cannot fix the many-terabyte cases.

The default disk guard stops the entire batch if free space drops below 2 GiB (rather than risking a full filesystem). Python and the C++ transform are sequential; the runner intentionally runs only one rectangle at once, so it does not multiply RAM demand.

## Useful commands

Test a short range before committing:

```bash
python3 mrc_batch_generate.py --r-min 11 --r-max 13 --c-max 15 \
  --out-dir ~/dev/mrc-data/data --memory-gb 64
```

Review which tables are within your RAM budget (does not change data):

```bash
python3 mrc_batch_generate.py --dry-run --memory-gb 64
```

Rerun the same command after an interruption: all completed `.DONE` tables are skipped and completed CRT primes of interrupted jobs are reused.

For logs, use `tail -f` on the append-only batch log. The runner exits with status 0 if everything was completed or already present, status 3 if it reached the end but some rectangles were skipped/failed, status 2 if disk space triggered a stop, status 1 on fail-fast exit, or status 130 on keyboard interruption. An exit status of 3 is **expected** for the complete width 1..24 sweep with current memory limits.

## Tested

- Generated 1x1 through 3x4 (nine total), each with a zero-byte `r.c.DONE` marker.
- Compared generated `3.4.csv` byte-for-byte with the baseline bundle: match.
- Reran the same nine jobs: all correctly detected as complete and skipped.
- Removed `2.3.DONE` and reran: detected existing complete `2.3.csv` and restored an empty marker without regenerating.

No full 684-rectangle benchmark was attempted; large cases can run for a long time.
