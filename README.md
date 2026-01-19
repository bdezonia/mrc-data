# Exact Enumeration Data for m(r,c,o,a)

## Overview

This repository contains exact enumeration data for the combinatorial function

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%2C" />

the number of ways to place o occupied cells in an r × c grid such that exactly a horizontal/vertical adjacencies occur between occupied cells.

Here:

- <img src="https://latex.codecogs.com/svg.latex?r%2C%20c%20%5Cge%201" /> are the grid dimensions
- <img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20o%20%5Cle%20rc" /> is the number of occupied cells
- <img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20a%20%5Cle%202rc%20-%20r%20-%20c" /> is the number of adjacencies

These tables were generated using optimized dynamic-programming enumeration methods and are intended for:

- Theoretical analysis
- Verification of conjectures
- Benchmarking approximations
- Reproducible research

---

## Mathematical Definition

Let <img src="https://latex.codecogs.com/svg.latex?G_%7Br%2Cc%7D" /> be the r × c rectangular grid graph.
Then <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" /> counts subsets of o vertices whose induced subgraph contains exactly a edges.

Boundary conditions:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2C0%2C0%29%20%3D%201%2C%20%5Cqquad%0Am%28r%2Cc%2Crc%2C2rc-r-c%29%20%3D%201." />

Symmetry:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%20%3D%20m%28c%2Cr%2Co%2Ca%29." />

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

<img src="https://latex.codecogs.com/svg.latex?m%286%2C9%2C4%2C2%29%20%3D%2093079." />

---

## Data Generation

All tables were computed using exact dynamic programming over grid column states, with:

- Symmetry reduction <img src="https://latex.codecogs.com/svg.latex?r%20%5Cle%20c" />
- Bitmask representations of column occupancy
- Edge-tracking for adjacency counts
- Arbitrary-precision integer arithmetic

The algorithms were designed for correctness and completeness, not merely approximation.

For small grids, all values of o and a are enumerated exhaustively.

---

## Known Notes & Edge Cases

- Very small grids (e.g. <img src="https://latex.codecogs.com/svg.latex?3%20%5Ctimes%203" />) may exhibit degenerate behavior due to boundary constraints.
- For <img src="https://latex.codecogs.com/svg.latex?r%2Cc%20%5Cge%205" />, the distributions of a become well-behaved and suitable for asymptotic modeling.
- The case <img src="https://latex.codecogs.com/svg.latex?o%3D0" /> always satisfies <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2C0%2C0%29%3D1" />.

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
