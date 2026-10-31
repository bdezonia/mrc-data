# MRC archive validation kit

Independent audit of the existing `mrc_data` CSV archive, intended as the foundation for a methods/data publication.

Requirements: Python 3.9+, standard library only. It does not import or modify the MRC statistics tool. It expects `r.c.csv` with header `r,c,o,a,count` and final line `.DONE.`; sparse and dense tables are accepted.

## Run on the full archive

```bash
python3 mrc_archive_validate.py ~/dev/mrc-data/data --report mrc_validation_report.csv
```

It scans **every** named `r.c.csv` under the given folder, checking every occupancy's exact total and coupling moments of orders 1, 2, 3, plus exact boundary cases. For `rc<=16`, it compares every value with brute-force enumeration. For minimum side <=6, it additionally compares two polynomial fingerprints with an independent straightforward transfer calculation (not the butterfly). Logs PASS/FAIL for each table and writes a CSV report with checks performed and SHA-256 digests. One bad table does not stop the remaining checks; an error sets exit code 1.

For large archives this may take a while. To begin with the least expensive audit, disable optional additional checks:

```bash
python3 mrc_archive_validate.py ~/dev/mrc-data/data \
    --brute-cells 0 --transfer-width 0 \
    --report mrc_validation_fast.csv
```

To make the transfer cross-check more thorough at additional computational cost, increase `--transfer-width 6` to `7` or `8`.

## Test

```bash
python3 -m unittest -v test_mrc_archive_validate.py
```

The test suite independently constructs small exact tables by brute force. It also deliberately corrupts tables so that their totals and lower moments are unchanged, verifying that the third-moment test and the independent transfer fingerprints detect the corruption.

## Files

- `mrc_archive_validate.py`: independent validator.
- `test_mrc_archive_validate.py`: its tests.
- `MRC_VALIDATION_PROOF_NOTE.md`: rigorous recurrence and butterfly proofs, graph-moment identities, validation limitations.
- `sample_data/3.3.csv`: tiny synthetic reference table, not a claim about the public repo.

This package is a **first step**, not a certificate that the full archive was validated. Its output report from an actual archive run is the evidence needed for the paper.
