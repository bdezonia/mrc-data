# MRC fast butterfly v2 — source audit and mathematical certification argument

**Audit date:** 2026-10-31  
**Scope:** user-supplied `mrc_fast_transform.cpp` (ragged kernel), `mrc_fast_transform_dense_reference.cpp`, `mrc_fast_generate.py`, tests, and batch-runner source.  
**Outcome:** **PASS for the mathematical kernel and observed test cases**, with one **cache-integrity hardening issue** and normal limits on claims about a published dataset.

## 1. Problem and exact transfer equation

Let an `r × c` grid contain `N=rc` cells and `E=2rc-r-c` undirected nearest-neighbor edges. For a subset of occupied cells, write `o` for the number selected and `a` for the number of edges with both endpoints occupied. `m(r,c,o,a)` counts these subsets.

Orient the rectangle as `h` rows, each of width `w=min(r,c)`. For each row mask `M` define `b(M)=popcount(M)`, `q(M)=popcount(M & (M<<1))`, and `v(P,M)=popcount(P & M)`. With the single initial state `F_0(0)=1`, recursively define

`F_i(M;x,y) = x^b(M) y^q(M) Σ_P [y^v(P,M) F_{i-1}(P;x,y)]`.

Every binary configuration corresponds to one unique sequence of masks. The added row introduces precisely `b(M)` occupied cells, `q(M)` internal couplings, and `v(P,M)` couplings to the preceding row. Induction on the number of rows proves that `Σ_M F_h(M;x,y) = Σ_(o,a) m(r,c,o,a) x^o y^a`.

This is a mathematical proof for all finite rectangular grids, independent of implementation or available RAM.

## 2. Exact butterfly transformation

The inter-row kernel has `K(M,P)=y^popcount(M&P)` and factors into `w` copies of `[[1,1],[1,y]]`. For each bit, masks differing only in that bit undergo

`(f0,f1) ↦ (f0+f1, f0+y f1)`.

The ragged C++ kernel executes this pair operation at `mrc_fast_transform.cpp:126-147`. Its descending loop preserves the old coefficient `f1[j-1]` before it is overwritten; thus each pass implements precisely the one-bit polynomial transform. The row occupancy and internal coupling shifts appear at lines 148-162. The conventional `--algorithm naive` mode at lines 163-183 independently realizes the same transfer by explicit mask-pair enumeration. The final mask sum occurs at lines 193-205.

The dense reference kernel applies the same mathematical butterfly with rectangular storage. The ragged and dense layouts are equivalent provided no nonzero polynomial coefficient is pruned; this is established in Section 3.

## 3. Rigorous proof that ragged coefficient pruning is safe

After processing a partial grid with `N` vertices and `E` edges, every placement with `o` occupied vertices obeys

`L(N,E,o) = max(0,E-4(N-o)) ≤ a ≤ U(N,E,o) = min(E,2o)`.

**Proof of lower bound:** Delete the `N-o` vacant vertices from the full graph. Each vertex is incident to at most four edges, so deletion removes at most `4(N-o)` distinct edges. Remaining edges are exactly occupied–occupied edges. **Proof of upper bound:** At most `E` edges can survive; each occupied vertex has degree at most four, and each occupied–occupied edge contributes two to the occupied degree sum, so `2a≤4o`.

The C++ storage per occupancy is `[L,U+w]` for intermediate layers and `[L,U]` at the final layer (`Block` lines 64-103). Each one-bit butterfly multiplication by `y` raises the coupling degree by at most one, while sums do not decrease the minimum degree. Thus after `k≤w` passes, all nonzero coefficients lie in `[L,U+k]`; the allocated `+w` padding suffices.

For a particular destination mask `M`, the kernel adds exactly `popcount(M&P)≤popcount(M)` vertical couplings. The copy restriction at lines 148-162 therefore removes only coefficients guaranteed to be zero. Applying the true new-row occupancy and horizontal shifts produces the next recurrence without losing nonzero entries. No probabilistic or approximate truncation occurs.

The source's `addmod` uses 32-bit unsigned sums of residues `<p≤2^31−1`; `2(p−1)≤2^32−4`, so its addition cannot overflow 32 bits. Modular computations are therefore exact under the selected prime modulus. All operations use integer arithmetic.

## 4. Why Chinese remainder reconstruction is exact

The Python driver chooses distinct 31-bit primes `p_i`, continuing until `P=∏ p_i > 2^N` (`mrc_fast_generate.py:19-57`). The source's Miller–Rabin bases `(2,7,61)` are a deterministic primality test for the 31-bit input range. Each MRC coefficient satisfies `0≤m(r,c,o,a)≤C(N,o)≤2^N<P`.

The CRT update at lines 123-128 computes the unique representative in `[0,P)` with the required residues, adding one prime at a time. Since the true count lies in that same interval, the reconstructed representative equals the true nonnegative integer (assuming the per-prime kernel returned the correct residues). Big integers in Python prevent CRT arithmetic overflow. The driver verifies all exact occupancy marginals and writes a dense CSV with terminal `.DONE.` only after reconstruction (`mrc_fast_generate.py:136-154`).

**Consequent theorem:** For the specified finite domain supported by machine/index limits, if the uploaded C++ and Python code executes with defined semantics and the unmodified modular results are used, the emitted CSV coefficients equal `m(r,c,o,a)` exactly. This is a mathematical argument linked to reviewed source; it is not a formally machine-verified implementation proof.

## 5. Executed tests in this audit

Run on copies of the uploaded source using Linux/GNU C++17 and Python 3:

* Supplied `test_mrc_fast_generate.py`: all brute, butterfly-vs-naive modular, and multi-prime CRT tests passed.
* Supplied `test_mrc_ragged_against_dense.py`: all seven byte-for-byte modular comparisons passed, including `10×12`.
* New independent `mrc_kernel_additional_tests.py`: **27 different rectangles**, each exhaustively enumerated up to **16 cells** with all coefficients compared under primes/moduli **3**, **65537**, and **2147483647**; **81 complete modular comparisons passed**.
* The same 81 comparisons, with the C++ kernel built using `-fsanitize=undefined -fno-sanitize-recover=all`, also passed with no sanitizer findings.
* An additional **7×9 full CRT comparison** against the C++ naive mask-pair implementation matched **byte-for-byte across all 7,104 output coefficients**, using **three primes**.

Earlier supplied `RESULTS.txt` reports further successes (including an independent `12×12` modular coefficient comparison), but those results were not re-executed during this audit.

The uploaded `mrc_validation_report.csv` records **522 passing files** with **0 failures**, **57,657,099 rows**, and **14,667,218 nonzero coefficients**; **27 full brute-force** and **225 modular transfer-fingerprint** archive checks were recorded. Those results are from the user's previously completed run; the entire 522-file archive was **not re-run here**. The snapshot checksum manifest bundled with this report is derived from that CSV, and should be compared against the actual release files when freezing the archive.

## 6. Finding: cached-prime payload integrity is not verified

The driver reads cached modular result files with `read_mod`, checking header fields, dimensions, and exact length, but not authenticating the payload (`mrc_fast_generate.py:60-79,102-109`). In a controlled **3×3 one-prime** experiment, swapping two different residues within the same occupancy left the marginal sum unchanged. The cache was accepted, the generated CSV changed, and the generator still reported success. This is a restart/cache-integrity concern; it is **not evidence of any error in the archived data** and is independent of the transfer/butterfly correctness proof.

Recommended hardening before a tagged public generator release: maintain a SHA-256 for every cached prime result when created and verify it on resume, and optionally check modular coupling moments for cached residues. Hashes alone must be stored separately from the payload to detect accidental alteration; no simple checksum replaces independent reproduction. If trusting old cached files, regenerate them or perform an independent validation before publication. The existing archive audit checks moment identities up to degree three and additional targeted comparisons.

A related restart issue: `mrc_batch_generate.py` trusts an existing zero-byte `r.c.DONE` plus a nonempty CSV without rechecking its contents. This is reasonable for routine continuation but not a publication validation step. Use the separate archive validator and SHA manifest for a release.

**Portability limitations:** C++ emits raw host-endian `uint32_t` data while Python reads little-endian. The audited execution environment is Linux/x86-64 little-endian; use an explicitly little-endian C++ writer for portable reproducibility. `__builtin_popcount` and `-march=native` are compiler/platform-specific. The implementation limits mask width to `<24` and available memory, but the theorem has no such limit.

## 7. Candidate release snapshot update (from separate user-run validator)

The 2026-10-31 source audit above was made when the archive contained **522 tables**; its source and runtime tests should be read as a historical record. A subsequent user-run `mrc_validation_report_v2.csv` covered **524 tables**, with **524 PASS / 0 FAIL**, **58,432,605 dense coefficient records** and **14,863,002 nonzero coefficients**. The new files were `17.26.csv` and `17.27.csv`; all 522 older files retained their earlier reported SHA-256 digests. For the 524-table report, all tables passed occupancy totals, factorial moments through order three, and special boundary distributions; 27 smaller tables passed full brute-force checks, and 225 passed two modular polynomial fingerprints.

The repository release candidate contains a **normalized copy** of the later report under `mrc_validation_report.csv` (its `file` column changed to portable `data/<r>.<c>.csv` paths) and a newly generated 524-entry `SHA256SUMS`. Those hashes originate from the user's local validation run; they must be checked against the **actual released data** before a tag is created. No further full-archive validation has been executed in the environment preparing this release candidate.

The earlier `mrc_source_sha256.csv` is intentionally omitted here: its filenames include an upload-local `mrc_batch_generate(1).py` and should not be presented as hashes of the eventual GitHub commit. Generate source hashes anew from the exact tagged source if desired.

## 8. Release recommendation and publication claim

1. Keep the currently audited generator source and reference tests unchanged during an active long calculation. For the later tagged release, harden prime-cache validation and preserve a complete source SHA-256 manifest.
2. Freeze a versioned `mrc_data` archive snapshot, verifying every actual CSV SHA-256 against the candidate 524-file `paper-verifications/SHA256SUMS` (and checking there are no extra `r.c.csv` tables in the tag).
3. Publish the recurrence/butterfly/CRT proofs, executable audit and reports. Keep historical source-audit results distinguishable from the subsequent 524-table validation.
4. State explicitly that normalization/moment/fingerprint checks are strong independent **computational checks**, not an isolated formal proof of all bytes in the released archive.

Suggested defensible language: *"The coefficients are calculated by an exact integer algorithm whose row recurrence, butterfly factorization, and reconstruction bounds are proved. All 524 files in the released archive snapshot passed independent combinatorial checks; the precise computational cross-check coverage and SHA-256 digests are supplied for reproducibility."*
