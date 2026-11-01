# MRC archive validation: mathematical foundations and reproducibility

**Status:** The enumeration recurrence and tensor factorization are proved for arbitrary finite rectangles. The separate release-candidate report records computational checks on 524 archived CSV files (524 PASS, 0 FAIL). These checks, while extensive, are not a formal machine proof of every coefficient. The report refers to the candidate snapshot, which must be matched by SHA-256 to the final tagged data files.

## Definition

For the grid graph on an `r × c` rectangle, let `N = rc` and `E = r(c−1)+c(r−1)`.
A configuration is a subset of occupied vertices. Its occupancy `o` is the number of selected vertices; its coupling count `a` is the number of edges whose endpoints are both selected. Then `m(r,c,o,a)` is the number of configurations with these values, and

`G_{r,c}(x,y) = sum_{o,a} m(r,c,o,a) x^o y^a`.

## Theorem 1: row-mask recurrence

Choose an orientation so that a row has `w` cells and the rectangle has `h` rows. For a row mask `M`:

- `b(M)` is its number of set bits;
- `q(M)` is the number of consecutive set-bit pairs in that row;
- `v(P,M)` is the number of set bits in `P & M`.

Set `F_0(0;x,y)=1` with all other values zero. For `i>=1` define

`F_i(M;x,y) = x^{b(M)} y^{q(M)} sum_P y^{v(P,M)} F_{i−1}(P;x,y)`.

Then `G_{r,c}(x,y)=sum_M F_h(M;x,y)` and `m(r,c,o,a)=[x^o y^a]G_{r,c}(x,y)`.

**Proof.** Every configuration of the first `i` rows has a unique last row `M` and a unique preceding row `P`. The added row contributes exactly `b(M)` occupied cells and `q(M)` horizontal couplings. The only new inter-row couplings are the `v(P,M)` vertical ones. All other contributions are already accounted for by the first `i−1` rows. Induction on `i` counts each binary configuration once, with precisely its occupancy and coupling exponents. Summing over final masks includes every configuration. QED.

## Theorem 2: butterfly factorization

The inter-row kernel is `K_{M,P}=y^{popcount(M & P)}`. For a single bit, with row/column bit values `0,1`, the kernel is

```
K_1 = [ [1, 1],
        [1, y] ].
```

Since `popcount(M&P)=sum_j M_j P_j`, the full kernel factors as

`K_w = K_1 ⊗ K_1 ⊗ ... ⊗ K_1` (`w` factors).

Thus applying `K_w` can be performed as `w` successive bitwise butterfly passes. This **establishes the algebraic equivalence** of the transfer operation and the butterfly factorization. It does **not** by itself verify that a particular optimized source implementation performs those passes faithfully; that requires a code audit or computational cross-check.

## Exact independent CSV checks

Write `A` for the number of couplings in a uniformly selected subset of `o` vertices. In the following equations, the sums are **unnormalized sums over every configuration**, and we use `C(n,k)=0` for invalid arguments.

1. `sum_a m(o,a) = C(N,o)`.
2. `sum_a a m(o,a) = E C(N−2,o−2)`.
3. `sum_a C(a,2) m(o,a) = S C(N−3,o−3) + D C(N−4,o−4)`, where `S=sum_vertex C(degree,2)` counts pairs of edges meeting at one vertex and `D=C(E,2)−S` counts disjoint pairs.
4. `sum_a C(a,3) m(o,a) = C4 C(N−4,o−4) + C5 C(N−5,o−5) + C6 C(N−6,o−6)`, where `Ck` counts 3-edge subsets touching `k` distinct vertices.

The fourth identity follows by choosing three present edges, then selecting the remaining occupied vertices arbitrarily. For a rectangular grid (which has no triangles), these three edge classes can be computed without enumeration of configurations:

`P = sum_{edges {u,v}} (degree(u)−1)(degree(v)−1)` (3-edge simple paths),

`T = sum_vertex C(degree,3)` (3-edge stars),

`C4=P+T; C5=S(E−2)−2P−3T; C6=C(E,3)−C4−C5`.

The code checks all four identities **for every occupancy** in every file, using only exact Python integers. The moment identities are an independent consequence of the grid graph and fixed-occupancy sampling; they do not reuse the butterfly code.

It also checks exact special distributions for `o=0,1,2,3,N−1,N`, the CSV schema, the `.DONE.` terminator, nonnegative integer counts, valid indices, and duplicate entries.

For `N<=16` by default, the validator independently enumerates all `2^N` occupancy configurations and checks each coefficient. For grid **minimum dimension <=6** by default, it independently evaluates the row-mask recurrence using a simple quadratic-in-mask-count transfer (no butterfly), at two predetermined integer points modulo two different primes, and compares the resulting polynomial fingerprints with those of the CSV. Fingerprints are high-confidence checks but not mathematical certificates of polynomial identity.

A full reproducibility case for the public archive should provide a **versioned generator**, an executable audit, the dataset release hash manifest, an explicit list of covered rectangles, and ideally independent full coefficient reproduction of some tractable overlap region. No finite collection of moment identities alone proves all individual coefficients.

## Reproducible command

```bash
python3 -m unittest -v test_mrc_archive_validate.py
python3 mrc_archive_validate.py ~/dev/mrc-data/data --report mrc_validation_report.csv
```

Performance controls:

```bash
# Skip brute force; expand the independent transfer comparison to width 7
python3 mrc_archive_validate.py ~/dev/mrc-data/data --brute-cells 0 --transfer-width 7

# Structural and exact moment checks only (fastest)
python3 mrc_archive_validate.py ~/dev/mrc-data/data --brute-cells 0 --transfer-width 0
```

The report contains the SHA-256 digest of every passing file. Freeze and archive that manifest alongside a tagged GitHub release before referring to the dataset version from a paper.

**Publication wording:** "The enumeration recurrence and its factorized kernel are proved exactly. The released coefficient tables are produced by exact-integer implementations and are subjected to independent combinatorial identity checks, targeted exhaustive enumeration, and modular transfer checks; our validation report identifies the checks performed for each table." Do not call the released files formally verified merely because they passed these checks.
