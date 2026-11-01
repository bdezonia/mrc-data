# MRC statistics and thermodynamics

This directory contains the **current** fixed-occupancy statistics and
lattice-gas thermodynamics client for the `mrc-data` archive.

- `mrc_data_statistics.py`: single observation, CSV batch, thermodynamics.
- `MRC_STATISTICS_README.md`: statistical definitions, examples and limitations.
- `test_mrc_data_statistics.py`, `test_mrc_thermodynamics.py`,
  `test_mrc_release_safety.py`: independent tests.
- `sample_data/3.3.csv`: tiny brute-force reference table used by the examples.
- `example_observations.csv`, `example_results.csv`,
  `sample_thermo_results.csv`: reproducible demonstration inputs/outputs.
- `paper-verifications/`: separately curated archive validation evidence;
  **not included in this statistics update**, and should not be removed.

From repository root (`~/dev/mrc-data`):

```bash
python3 code/statistics/mrc_data_statistics.py 6 8 12 14 --data-dir data
cd code/statistics
python3 -m unittest -v test_mrc_data_statistics.py test_mrc_thermodynamics.py test_mrc_release_safety.py
```

For example calculations, see `MRC_STATISTICS_README.md`. The script reads
finished `data/r.c.csv` files; it does not modify or generate them.
