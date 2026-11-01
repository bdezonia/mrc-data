# MRC coefficient archive: validation and release evidence

This directory documents the validation of the **524-table candidate release snapshot** of
`mrc-data`. Validation is distinct from the mathematical proof of the enumerator.
The complete MRC data tables remain under `data/` at the repository root. Generator
sources and statistical tools are maintained elsewhere under `code/`; this folder is
validation/release evidence only.

## Recorded snapshot (pre-release; do not confuse with a frozen Git tag)

- Tables: **524 PASS, 0 FAIL**.
- Dense coefficient records: **58,432,605**, of which **14,863,002** are nonzero.
- Full brute-force coefficient comparisons: **27** tables (all with at most 16 cells).
- Independent transfer checks: **225** tables, with two polynomial evaluations mod distinct primes (these are fingerprints, not full coefficient comparisons).
- All 524 tables passed occupancy normalization, first-through-third factorial-moment identities, and exact special-occupancy checks.
- Additions since 522-table predecessor: `17.26.csv` and `17.27.csv`. Previous 522 digests unchanged.
- Rectangles covered: all `1 <= r <= 15`, `r <= c <= 40`; all `16 <= c <= 32` for `r=16`; all `17 <= c <= 27` for `r=17`; and `18.18.csv`.
- Boundary conditions are **open** and occupancy is fixed in the statistical null model.

## Repository layout

The paths in the instructions below match this repository structure:

```text
~/dev/mrc-data/
├── data/                         # r.c.csv tables
└── code/
    └── statistics/
        └── paper-verifications/
            ├── README.md
            ├── mrc_validation_report.csv
            ├── SHA256SUMS
            ├── verify_release_snapshot.py
            ├── mrc_archive_validate.py
            ├── test_mrc_archive_validate.py
            ├── MRC_VALIDATION_PROOF_NOTE.md
            └── audit/
```

The corrected verifier locates `mrc_validation_report.csv` and `SHA256SUMS`
relative to **its own script location**, while `--repo-root` points to the directory
containing `data/`. This avoids assuming `paper-verifications/` is at the
repository root.

## Files

| Path | Role |
| --- | --- |
| `mrc_archive_validate.py` | Independent exact-integer CSV validator; unchanged from the tested version. |
| `test_mrc_archive_validate.py` | Seven self-contained unit-test groups. |
| `MRC_VALIDATION_PROOF_NOTE.md` | Recurrence, butterfly factorization, and independent moment identities. |
| `mrc_validation_report.csv` | Portable 524-table report; `file` column normalized to `data/<r>.<c>.csv`. |
| `SHA256SUMS` | SHA-256 digest for every CSV in that report, relative to repository root. |
| `verify_release_snapshot.py` | Pre-tag check of actual CSV hashes, set completeness, and report/manifest agreement. |
| `audit/MRC_AUDIT.md` | 2026-10-31 source review (522-table historical context) with 524-table addendum and known limitations. |
| `audit/mrc_audit_tests.py` | Additional independent brute-force/modular kernel test; requires `--kernel`. |
| `audit/additional_kernel_tests.log` | Recorded output of the 27-rectangle, 81-modular-comparison audit. |

The original machine-local 524-table report was named `mrc_validation_report_v2.csv`.
This copy modifies **only the file paths**, not any counts, statuses, or hashes.
SHA-256 of original, unmodified report: `b332e5d52d3901ec5c651b86feb450b8fa911f245d1eda875b862b8891ecf15a`.
The 522-table predecessor and the duplicate original sanitizer test log are retained outside this release candidate, rather than included here.

## Run validation on an archive

From the repository root:

```bash
python3 -m unittest discover \
    -s code/statistics/paper-verifications \
    -p 'test_mrc_archive_validate.py' -v

python3 code/statistics/paper-verifications/verify_release_snapshot.py \
    --repo-root .
```

The second command compares every file hash and rejects missing or unexpected `r.c.csv` tables. **Do this after stopping or isolating the generator**, so the data tree cannot change during the check. Because the manifest freezes exactly 524 tables, newly generated tables will intentionally cause an "extra tables" failure unless you isolate the tagged 524-table snapshot. This was **not** run against the full repository as part of preparing this candidate, because the data files were not supplied in this ZIP.

To independently rerun the full mathematical audit (it scans all tables and may be costly):

```bash
python3 code/statistics/paper-verifications/mrc_archive_validate.py data \
    --report /tmp/mrc_validation_rerun.csv
```

For separate kernel audit tests, first build the C++ generator from its own source directory, then supply the **absolute** path of that executable:

```bash
python3 code/statistics/paper-verifications/audit/mrc_audit_tests.py \
    --kernel /absolute/path/to/mrc_fast_transform
```

## Scientific and software limitations

- The recurrence, butterfly factorization and CRT bound establish mathematical exactness of the algorithm under their stated assumptions. The report provides **computational evidence** of the published coefficients, not a formal per-byte proof.
- `SHA256SUMS` is derived from the user-run validation report; it is **not independent authentication** of the archive. It must match files in the release commit.
- The earlier source review identified a prime-cache integrity gap and a `.DONE`-marker restart trust assumption. These do not imply errors in the validated archive, but should be documented and addressed in future generator improvements.
- The release should contain the generator, dense reference, statistical calculator (including thermodynamics), and build/test instructions elsewhere in the repository, all verified to match the desired tagged source.
- Future data additions require a new report and version, not a change to this release snapshot.
