# Release-candidate cleanup (proposed; not applied to your repository)

Source reviewed: the uploaded `paper-verifications.zip` (17 ZIP entries including two directories).

## Original files omitted and why

- `mrc_validation_report.csv`: old 522-table report; preserve offline or in a historical archive, not beside the canonical 524-table report.
- `mrc_validation_report_v2.csv`: superseded by path-normalized 524-table canonical `mrc_validation_report.csv`. Only the `file` paths were changed; no counts/status/hashes were altered.
- `audit/mrc_checksums.csv`: 522-only manifest, replaced by full 524-table `SHA256SUMS`.
- `audit/mrc_source_sha256.csv`: snapshot filename includes `mrc_batch_generate(1).py`; hashes must be regenerated from actual committed canonical paths. Do NOT claim it covers the tagged source.
- `audit/test_ubsan.log`: byte-for-byte identical to `audit/test_extra.log` (both SHA-256 59a4b199d0ef7e8f08a0c24fc25b116c10e87e7c7279a149b81055eb639b4d9a).
- `example_validation_report.csv`, `sample_data/3.3.csv`: illustrative, not necessary since the validator tests generate exact small tables themselves.

## Original files kept or revised

- Unmodified: validator and seven tests.
- Status wording revised: proof note.
- Historical audit preserved with clearly labeled 524-table addendum.
- Extra kernel tests: fixed broken default kernel path by requiring explicit `--kernel`.
- New: 524-file SHA256SUMS, pre-release snapshot checker, release-oriented README.

**Important:** This is an editorial candidate, not an audit of the actual repository files. Run the snapshot verifier against `~/dev/mrc-data` after isolating the generator; resolve any failures before tagging. The two new 17.x tables passed the reported moment and boundary checks, not full independent re-enumeration.

SHA-256 of the original raw 524-row report: `b332e5d52d3901ec5c651b86feb450b8fa911f245d1eda875b862b8891ecf15a`.
