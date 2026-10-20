# Validation record, 18 October 2026

Mathematical recurrence implemented:

`F_{h+1}(T;x,y)=x^|T| y^horiz(T) sum_S F_h(S;x,y) y^|S&T|`.

- Brute-force cross-check of **all nonzero and zero coefficients** for grids 1×1, 1×6, 2×5, 3×4, 3×5 and 4×4: PASS.
- Independent conventional dense mask-pair C++ modular DP for 4×7, 5×7, 6×7, 7×9: BYTE-FOR-BYTE MATCH.
- Exact multiple-prime CRT for 5×7 compared to conventional dense mask-pair C++ DP: BYTE-FOR-BYTE MATCH.
- 12×12 modular data before and after applying geometry-derived coefficient pruning: BYTE-FOR-BYTE MATCH.
- Full 10×12 exact CSV from four 31-bit primes compared to archived `../data/10.12.csv` in user-supplied `all(2).zip`: BYTE-FOR-BYTE MATCH, 525,378 bytes, SHA-256 `c8631e0aa16bb7cfe786bb178293a19db204fdf62a0b8fac2c70938a798943af`.
- All 38,425 12×12 coefficients reduced modulo 2,147,483,647 compared to archived exact numbers: MATCH (not full CRT).
- Cache/resume of modular files: PASS for 5×7.

**Important**: These validations establish correctness within the tested domain and independently derive the recurrence. They do not yet benchmark full-scale performance against the existing sparse Java generator on the user's workstation. The original archive was *only* used after generation, to verify the output.

## Run reproducibly

    ./build.sh
    python3 test_mrc_fast_generate.py
    python3 mrc_fast_generate.py --r 10 --c 12 --out 10.12.csv --cache-dir 10.12.crt_cache
    python3 verify_mrc_archive.py --archive /path/to/all.zip --csv 10.12.csv
