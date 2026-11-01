#!/usr/bin/env python3
"""Check the proposed MRC CSV release against the frozen validation report.

From the repository root:
    python3 paper-verifications/verify_release_snapshot.py --repo-root .

Read-only; standard-library only. Ensures SHA hashes match and rejects
missing or extra r.c.csv files. The report and hashes must be generated
from an independent prior validation run, not from this program.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import re
import sys

TABLE = re.compile(r"[1-9][0-9]*\.[1-9][0-9]*\.csv\Z")


def file_digest(path):
    dig = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(4*1024*1024), b''):
            dig.update(block)
    return dig.hexdigest()


def run(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, default=Path('.'))
    args = p.parse_args(argv)
    root = args.repo_root.expanduser().resolve()
    folder = Path(__file__).resolve().parent
    report_path = folder / 'mrc_validation_report.csv'
    manifest_path = folder / 'SHA256SUMS'
    data = root / 'data'
    if not report_path.is_file() or not manifest_path.is_file() or not data.is_dir():
        p.error('expected paper-verifications/mrc_validation_report.csv, SHA256SUMS, and data/ under repo root')
    with report_path.open(newline='', encoding='utf-8') as fp:
        rows = list(csv.DictReader(fp))
    expected = {}
    errors = []
    if len(rows) != 524:
        errors.append(f'expected 524 report rows, found {len(rows)}')
    for row in rows:
        rel = row['file']
        if not rel.startswith('data/') or not TABLE.fullmatch(rel[5:]):
            errors.append(f'noncanonical report path: {rel}')
            continue
        if rel in expected:
            errors.append(f'duplicate report record: {rel}')
        if row['status'] != 'PASS' or len(row['sha256']) != 64:
            errors.append(f'nonpassing or malformed report row: {rel}')
        expected[rel] = row['sha256']
    manifest = {}
    with manifest_path.open(encoding='ascii') as fp:
        for line in fp:
            line = line.rstrip('\n')
            parts = line.split('  ', 1)
            if len(parts) != 2 or parts[1] in manifest:
                errors.append(f'bad or duplicate manifest line: {line[:110]}')
                continue
            manifest[parts[1]] = parts[0]
    if expected != manifest:
        errors.append('SHA256SUMS and report disagree')
    actual = {f'data/{p.relative_to(data).as_posix()}' for p in data.rglob('*.csv') if TABLE.fullmatch(p.name)}
    missing = sorted(expected.keys() - actual)
    extra = sorted(actual - expected.keys())
    if missing:
        errors.append(f'missing tables ({len(missing)}): {missing[:8]}')
    if extra:
        errors.append(f'extra tables ({len(extra)}): {extra[:8]}')
    verified = 0
    for rel, digest in expected.items():
        file = root / rel
        if not file.is_file():
            continue
        if file_digest(file) != digest:
            errors.append(f'SHA-256 MISMATCH {rel}')
        else:
            verified += 1
    if errors:
        for error in errors[:30]:
            print('FAIL:', error, file=sys.stderr)
        if len(errors)>30:
            print(f'...and {len(errors)-30} more', file=sys.stderr)
        return 1
    print(f'PASS: {verified} files match SHA-256; no missing or extra r.c.csv tables')
    return 0

if __name__ == '__main__':
    sys.exit(run())
