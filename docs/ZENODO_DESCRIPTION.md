# Exact Enumeration Data for the Grid Adjacency Function m(r,c,o,a)

## Overview

This dataset provides **exact combinatorial enumeration data** for the function

\[
m(r,c,o,a),
\]

the number of ways to place o occupied cells in an r × c rectangular grid such that exactly a horizontal/vertical adjacencies occur between occupied cells.

Each data file contains the full distribution of \( m(r,c,o,a) \) values for a fixed grid size (r,c), computed using a deterministic dynamic-programming (DP) algorithm.

All data are **dense**, **exact**, and **fully verified**.

---

## Contents

The dataset consists of CSV files of the form:

```
r.c.csv
```

For example:

```
5.8.csv
7.11.csv
9.15.csv
```

Each file contains rows of the form:

```
r,c,o,a,count
```

where:

- `r`, `c` — grid dimensions  
- `o` — number of occupied cells  
- `a` — number of adjacencies  
- `count` — exact value of \( m(r,c,o,a) \)  

All possible \( (o,a) \) pairs appear explicitly, including rows with `count = 0`.

Each file ends with the sentinel line:

```
.DONE.
```

---

## Data Properties

For each grid (r,c), the data satisfy:

\[
\sum_{o,a} m(r,c,o,a) = 2^{rc},
\]
\[
\sum_a m(r,c,o,a) = \binom{rc}{o},
\]

as well as the boundary conditions:

\[
m(r,c,0,0) = 1, \qquad
m(r,c,rc,2rc - r - c) = 1.
\]

These identities guarantee that every subset of grid cells is counted exactly once.

---

## Method of Generation

All values were computed using a custom **Java dynamic-programming algorithm** that enumerates all subsets of an r × c grid and tracks the number of induced adjacencies.

Key features:

- Deterministic computation  
- Exact integer arithmetic  
- No sampling or approximation  
- Symmetry exploitation <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%3Dm%28c%2Cr%2Co%2Ca%29" />  
- Multi-threaded scheduling for larger grids  

The code used to generate the data is included in the repository.

---

## Verification

Every CSV file is validated using an automated verification pipeline that checks:

- File format and sentinel correctness  
- Dense row structure  
- Value ranges  
- Global sum: \( 2^{rc} \)  
- Per-o sums: \( \binom{rc}{o} \)  
- Boundary conditions  

The verification scripts are included in:

```
code/verify_csv.py
code/verify_batch.py
```

The methodology is documented in:

```
docs/VERIFICATION_METHODOLOGY.md
```

---

## Theoretical Context

The function \( m(r,c,o,a) \) arises in the study of:

- Induced subgraphs of grid graphs  
- Adjacency-constrained configurations  
- Lattice combinatorics  
- Statistical mechanics models (e.g., lattice gases)  
- Combinatorial probability distributions  

Closed-form bounds for the minimal and maximal adjacency values are known in some regimes, but have **documented limitations** for certain grid geometries (e.g., odd×odd grids and small dimensions).

These limitations are described in:

```
docs/KNOWN_THEORY_LIMITATIONS.md
```

---

## Intended Use

This dataset is intended for:

- Exact combinatorial analysis  
- Benchmarking theoretical bounds  
- Model validation  
- Probability distribution studies  
- Algorithmic research on grid graphs  

The data are exact and suitable as a reference standard.

---

## License

This dataset is licensed under the Creative Commons Attribution 4.0
International (CC-BY 4.0) license.

You are free to use, share, and adapt the data, provided that
appropriate credit is given to the author.

---

## Citation

If you use this dataset, please cite:

> Barry DeZonia, *Exact Enumeration Data for the Grid Adjacency Function m(r,c,o,a)*, Zenodo, Year, DOI.

(To be replaced with the actual DOI once Zenodo assigns it)

---

## Contact

For questions, corrections, or collaboration:

Barry DeZonia  
United States  
GitHub: https://github.com/bdezonia/mrc-data
