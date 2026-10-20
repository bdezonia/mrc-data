#!/usr/bin/env python3
"""Unattended exact MRC table generation with resumable CRT and .DONE markers.

Calls mrc_fast_generate.py for each rectangle (never implements a second DP).
Requires Python >= 3.10 and the C++ kernel from the fast butterfly bundle.
"""

import argparse
import csv
import datetime as dt
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
GIB = 1024 ** 3


def two_layer_peak_bytes(w: int, h: int) -> int:
    """Replicate the peak two-layer coefficient allocation guard in C++."""
    w, h = sorted((w, h))
    masks = 1 << w
    previous = masks * (w + 1)  # initial state (o=0,a=0), with w padding
    peak = 0
    for i in range(h):
        next_o = (i + 1) * w
        next_a = (i + 1) * (w - 1) + i * w
        padding = w if i + 1 < h else 0
        upcoming = masks * (next_o + 1) * (next_a + 1 + padding)
        peak = max(peak, 4 * (previous + upcoming))
        previous = upcoming
    return peak


def read_tail(path: Path, count: int = 65536) -> list[bytes]:
    with path.open("rb") as inp:
        inp.seek(0, os.SEEK_END)
        size = inp.tell()
        inp.seek(max(0, size - count))
        block = inp.read()
    lines = block.splitlines()
    if size > count and lines:
        lines = lines[1:]  # first line might be cut off
    return lines


def complete_csv(path: Path, r: int, c: int, count_lines: bool) -> bool:
    """Check original CSV format, last data record and embedded sentinel.

    With count_lines=True, also check the exact number of dense data lines.
    Does not attempt to independently recheck every numeric coefficient;
    the generator itself checks exact occupancy marginals.
    """
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        with path.open("rb") as inp:
            if inp.readline().strip() != b"r,c,o,a,count":
                return False
        tail = read_tail(path)
        if len(tail) < 2 or tail[-1].strip() != b".DONE.":
            return False
        last_data = tail[-2].split(b",")
        edges = 2 * r * c - r - c
        if len(last_data) != 5 or last_data[:4] != [str(r).encode(), str(c).encode(), str(r*c).encode(), str(edges).encode()]:
            return False
        if int(last_data[4]) != 1:  # all occupied: exactly one configuration
            return False
        if count_lines:
            expected = (r*c+1)*(edges+1) + 2  # header + dense data + sentinel
            line_count = 0
            with path.open("rb") as inp:
                while True:
                    chunk = inp.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    line_count += chunk.count(b"\n")
            if line_count != expected:
                return False
        return True
    except (OSError, ValueError, OverflowError):
        return False


def create_done_marker(path: Path) -> None:
    """Write precisely zero bytes, then atomically rename into place."""
    fd, tempname = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    try:
        os.replace(tempname, path)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)
    assert path.stat().st_size == 0


def available_memory_gib() -> float | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as meminfo:
            for line in meminfo:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024 / GIB
    except (OSError, ValueError):
        return None
    return None


def timestamp() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def args_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--r-min", type=int, default=1)
    p.add_argument("--r-max", type=int, default=24)
    p.add_argument("--c-max", type=int, default=40)
    p.add_argument("--out-dir", type=Path, default=HERE.parent / "data", help="destination for r.c.csv and r.c.DONE")
    p.add_argument("--cache-root", type=Path, default=None, help="CRT pass cache root (default: OUT-DIR/.mrc_crt_cache)")
    p.add_argument("--memory-gb", type=float, default=64.0, help="C++ two-layer hard limit, in GiB")
    p.add_argument("--reserve-free-gb", type=float, default=8.0, help="leave at least this much currently available system RAM")
    p.add_argument("--min-free-disk-gb", type=float, default=2.0, help="stop batch if destination disk has less than this free space")
    p.add_argument("--keep-cache", action="store_true", help="retain CRT prime files even for successful rectangles")
    p.add_argument("--dry-run", action="store_true", help="print planned actions and memory estimates, make no data files")
    p.add_argument("--fail-fast", action="store_true", help="stop on first failed or ineligible rectangle (normally continue)")
    p.add_argument("--no-recover-existing", action="store_true", help="do not trust complete CSV files without markers; regenerate them")
    p.add_argument("--verbose-kernel", action="store_true", help="include the kernel's per-row diagnostics in the log")
    return p


def run(argv=None) -> int:
    p = args_parser().parse_args(argv)
    if p.r_min < 1 or p.r_max < p.r_min or p.c_max < p.r_max:
        raise SystemExit("Require 1 <= r-min <= r-max <= c-max")
    if p.memory_gb <= 0 or p.reserve_free_gb < 0 or p.min_free_disk_gb < 0:
        raise SystemExit("Memory and disk limits must be nonnegative, with memory-gb > 0")

    out_dir = p.out_dir.expanduser().resolve()
    cache_root = (p.cache_root or (out_dir / ".mrc_crt_cache")).expanduser().resolve()
    log_path = out_dir / "mrc_batch.log"
    index_path = out_dir / "mrc_batch_status.tsv"
    if not p.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        cache_root.mkdir(parents=True, exist_ok=True)
        if not (HERE / "mrc_fast_generate.py").is_file():
            raise SystemExit(f"Missing generator: {HERE / 'mrc_fast_generate.py'}")
        if not (HERE / "mrc_fast_transform").is_file():
            build = HERE / "build.sh"
            print(f"Kernel is missing; compiling with {build} ...", flush=True)
            subprocess.run(["bash", str(build)], cwd=HERE, check=True)

    summary: dict[str, int] = {}
    start = time.monotonic()
    total = sum(p.c_max - r + 1 for r in range(p.r_min, p.r_max + 1))
    print(f"MRC batch: {total} rectangles, r={p.r_min}..{p.r_max}, c=r..{p.c_max}")
    print(f"Output: {out_dir} ; two-layer limit: {p.memory_gb:g} GiB")
    print("Kernel supports widths 1..23; infeasible dimensions are reported, not attempted.")

    # fcntl flock: an interrupted process doesn't strand an unusable lock.
    lock_file = None
    if not p.dry_run:
        lock_file = (out_dir / ".mrc_batch.lock").open("a+")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(f"Another batch process has locked {out_dir}")

    log = None
    index = None
    if not p.dry_run:
        log = log_path.open("a", encoding="utf-8", buffering=1)
        fresh = not index_path.exists() or index_path.stat().st_size == 0
        index = index_path.open("a", newline="", encoding="utf-8")
        writer = csv.writer(index, delimiter="\t")
        if fresh:
            writer.writerow(("timestamp", "r", "c", "status", "seconds", "estimated_peak_gib", "note"))
            index.flush()
    else:
        writer = None

    def say(message: str):
        line = f"[{timestamp()}] {message}"
        print(line, flush=True)
        if log:
            log.write(line + "\n")

    def record(r: int, c: int, status: str, elapsed: float, peak_gib: float, note: str = "") -> None:
        summary[status] = summary.get(status, 0) + 1
        if writer is not None:
            writer.writerow((timestamp(), r, c, status, f"{elapsed:.2f}", f"{peak_gib:.4f}", note))
            index.flush()

    try:
        for r in range(p.r_min, p.r_max + 1):
            for c in range(r, p.c_max + 1):
                csv_path = out_dir / f"{r}.{c}.csv"
                done_path = out_dir / f"{r}.{c}.DONE"
                peak = two_layer_peak_bytes(r, c) / GIB
                t0 = time.monotonic()
                label = f"{r}x{c}"

                if done_path.exists() and csv_path.is_file() and csv_path.stat().st_size > 0:
                    # We trust the zero-byte completion marker left by this or a past run.
                    if done_path.stat().st_size == 0:
                        record(r, c, "already_done", 0, peak)
                        continue
                    say(f"WARN {label}: nonempty .DONE file; checking CSV before repair")

                if csv_path.exists() and not p.no_recover_existing and complete_csv(csv_path, r, c, count_lines=True):
                    if not p.dry_run:
                        create_done_marker(done_path)
                    say(f"RECOVERED {label}: existing complete CSV; created zero-byte {done_path.name}")
                    record(r, c, "recovered", time.monotonic() - t0, peak)
                    continue

                reason = None
                if r >= 24:
                    reason = "C++ prototype supports widths < 24"
                elif peak > p.memory_gb:
                    reason = f"peak two-layer estimate {peak:.2f} GiB exceeds {p.memory_gb:g} GiB limit"
                elif (available_memory_gib() is not None and
                      peak + p.reserve_free_gb > available_memory_gib()):
                    reason = f"system MemAvailable below peak {peak:.2f} GiB + reserve {p.reserve_free_gb:g} GiB"

                if reason:
                    say(f"SKIP {label}: {reason}")
                    record(r, c, "skipped", time.monotonic() - t0, peak, reason)
                    if p.fail_fast:
                        return 1
                    continue

                if p.dry_run:
                    say(f"WOULD GENERATE {label}, peak estimated two-layer RAM {peak:.2f} GiB")
                    record(r, c, "planned", 0, peak)
                    continue

                disk_free = shutil.disk_usage(out_dir).free / GIB
                if disk_free < p.min_free_disk_gb:
                    say(f"STOP: only {disk_free:.2f} GiB free disk space (limit {p.min_free_disk_gb:g} GiB)")
                    record(r, c, "stopped_disk", time.monotonic()-t0, peak, f"disk_free_gib={disk_free:.3f}")
                    return 2

                if done_path.exists():
                    done_path.unlink()  # never leave a positive completion marker for an unfinished CSV
                job_cache = cache_root / f"{r}.{c}"
                job_cache.mkdir(parents=True, exist_ok=True)
                cmd = [sys.executable, str(HERE / "mrc_fast_generate.py"),
                       "--r", str(r), "--c", str(c), "--out", str(csv_path),
                       "--memory-gb", str(p.memory_gb), "--cache-dir", str(job_cache)]
                if p.verbose_kernel:
                    cmd.append("--verbose")
                say(f"START {label} peak two-layer RAM estimate={peak:.2f} GiB")
                try:
                    # Tee progress into console and persistent log, one line at a time.
                    with subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True,
                                          encoding="utf-8", errors="replace", bufsize=1) as child:
                        assert child.stdout is not None
                        for line in child.stdout:
                            sys.stdout.write(line)
                            sys.stdout.flush()
                            log.write(line)
                        exit_code = child.wait()
                    if exit_code:
                        raise subprocess.CalledProcessError(exit_code, cmd)
                    if not complete_csv(csv_path, r, c, count_lines=False):
                        raise ValueError("generator exited 0 but CSV header/sentinel/last record invalid")
                    create_done_marker(done_path)
                    if not p.keep_cache:
                        shutil.rmtree(job_cache, ignore_errors=True)
                    elapsed = time.monotonic() - t0
                    say(f"DONE {label} in {elapsed:.1f}s -> {csv_path.name} + {done_path.name} (0 bytes)")
                    record(r, c, "generated", elapsed, peak)
                except KeyboardInterrupt:
                    say(f"INTERRUPTED {label}: no .DONE created, cached completed primes preserved")
                    record(r, c, "interrupted", time.monotonic()-t0, peak)
                    return 130
                except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                    say(f"FAILED {label}: {exc}; no completion marker; cache preserved")
                    record(r, c, "failed", time.monotonic()-t0, peak, str(exc))
                    if p.fail_fast:
                        return 1
        say(f"FINISHED all {total} candidates in {(time.monotonic()-start)/60:.1f} min; statuses: {summary}")
        return 0 if not summary.get("failed") and not summary.get("skipped") else 3
    finally:
        if index:
            index.close()
        if log:
            log.close()
        if lock_file:
            lock_file.close()


if __name__ == "__main__":
    sys.exit(run())
