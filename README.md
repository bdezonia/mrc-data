# Exact Enumeration Data for \( m(r,c,o,a) \)

## Overview

This repository contains exact enumeration data for the combinatorial function

\[
m(r,c,o,a),
\]

the number of ways to place \( o \) occupied cells in an \( r \times c \) grid such that exactly \( a \) horizontal/vertical adjacencies occur between occupied cells.

Here:

- \( r, c \ge 1 \) are the grid dimensions
- \( 0 \le o \le rc \) is the number of occupied cells
- \( 0 \le a \le 2rc - r - c \) is the number of adjacencies

These tables were generated using optimized dynamic-programming enumeration methods and are intended for:

- Theoretical analysis
- Verification of conjectures
- Benchmarking approximations
- Reproducible research

---

## Mathematical Definition

Let \( G_{r,c} \) be the \( r \times c \) rectangular grid graph.
Then \( m(r,c,o,a) \) counts subsets of \( o \) vertices whose induced subgraph contains exactly \( a \) edges.

Boundary conditions:

\[
m(r,c,0,0) = 1, \qquad
m(r,c,rc,2rc-r-c) = 1.
\]

Symmetry:

\[
m(r,c,o,a) = m(c,r,o,a).
\]

---

## Repository Structure

```text
mrc-data/
├── code/        # DP generators and utilities
├── data/        # CSV tables for each (r,c)
├── docs/        # Misc documentation about this project
├── releases/    # Frozen DP release sets referencable as needed
├── README.md
└── CITATION.bib
```

Each CSV file contains rows of the form:

```text
r, c, o, a, count
```

Example:

```text
6, 9, 4, 2, 93079
```

meaning:

\[
m(6,9,4,2) = 93079.
\]

---

## Data Generation

All tables were computed using exact dynamic programming over grid column states, with:

- Symmetry reduction \( r \le c \)
- Bitmask representations of column occupancy
- Edge-tracking for adjacency counts
- Arbitrary-precision integer arithmetic

The algorithms were designed for correctness and completeness, not merely approximation.

For small grids, all values of \( o \) and \( a \) are enumerated exhaustively.

---

## Known Notes & Edge Cases

- Very small grids (e.g. \( 3 \times 3 \)) may exhibit degenerate behavior due to boundary constraints.
- For \( r,c \ge 5 \), the distributions of \( a \) become well-behaved and suitable for asymptotic modeling.
- The case \( o=0 \) always satisfies \( m(r,c,0,0)=1 \).

Any detected discrepancies are documented in the commit history.

---

## Citation

If you use this data, please cite:

> DeZonia, B. (2026). *Exact enumeration tables for grid occupancy adjacencies*.
> GitHub repository: https://github.com/bdezonia/mrc-data

For archival versions associated with publications, a DOI-linked snapshot will be provided via Zenodo.

---

## License

The code in this repository is being released with a MIT license.
 
The data in this repository is licensed under the Creative Commons
Attribution 4.0 International (CC-BY 4.0) license.

You are free to use, share, and adapt the data, provided that
appropriate credit is given to the author.

---

## Contact

Barry DeZonia  
Github: https://github.com/bdezonia
