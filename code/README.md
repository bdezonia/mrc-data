# Java Dynamic Programming Enumerator for m(r,c,o,a)

This directory contains a Java implementation of an exact dynamic-programming (DP) algorithm for computing the combinatorial function

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%2C" />

the number of ways to place o occupied cells in an r × c grid such that exactly a horizontal/vertical adjacencies occur.

The implementation is designed for **exact enumeration** using arbitrary-precision arithmetic and supports multi-threaded batch execution.

---

## Files

### `DP_optimized.java`

Core DP engine that:

- Implements a column-by-column (row-extension) dynamic program  
- Tracks:
  - Occupied cell count o  
  - Adjacency count a  
- Uses `BigInteger` for exact arithmetic  
- Outputs dense CSV tables with a `.DONE.` sentinel line  

Key features:

- Bitmask representation of column states  
- Horizontal and vertical adjacency tracking  
- Symmetry reduction: grids are transposed so that <img src="https://latex.codecogs.com/svg.latex?r%20%5Cle%20c" />  
- Deterministic, exact enumeration  

Main entry point:

```bash
java DP_optimized --r <rows> --c <cols> --out <output.csv> [--verbose]
```

This produces a CSV file of the form:

```
r,c,o,a,count
...
.DONE.
```

---

### `DPScheduler.java`

Batch scheduler that runs many `(r,c)` jobs in parallel using a thread pool.

Features:

- Automatically skips completed jobs using `.DONE` files  
- Supports configurable:
  - Maximum `r` and `c`
  - Number of threads
  - Output directory
- Runs all pairs `(r,c)` with `1 ≤ r ≤ rMax` and `r ≤ c ≤ cMax`  

Example usage:

```bash
java DPScheduler --rMax 10 --cMax 20 --threads 8 --out results/
```

Each completed job produces:

```
results/
  ├── 6.9.csv
  ├── 6.9.DONE
  ├── 7.12.csv
  ├── 7.12.DONE
  └── ...
```

---

## Algorithm Summary

The grid is processed one column at a time.  
Each column is represented by a bitmask of length `r` indicating which cells are occupied.

For each column state, the DP tracks:

- Total occupied cells so far o
- Total adjacencies so far a

Transitions between consecutive columns account for:

- Horizontal adjacencies within the new column  
- Vertical adjacencies between old and new columns  

At the final column, all states are aggregated to produce the full table:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29." />

All counts are **exact**.

---

## Computational Limits

Due to the exponential number of column states:

- The column height (<img src="https://latex.codecogs.com/svg.latex?r" />) is practically limited to **<img src="https://latex.codecogs.com/svg.latex?r%20%5Cle%2030" />**  
- Runtime grows rapidly with `r`  
- Large `c` values are feasible when `r` is small  

This implementation is intended for:

- Exact data generation  
- Verification of conjectures  
- Benchmarking approximations  

It is **not** intended for real-time or large-scale production use beyond these limits.

---

## Output Format

All CSV files follow the format:

```
r, c, o, a, count
```

Where:

- `r`, `c` = grid dimensions  
- `o` = number of occupied cells  
- `a` = number of adjacencies  
- `count` = exact value of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />  

The final line:

```
.DONE.
```

is used by the scheduler to mark completed jobs.

---

## Shell Scripts (Not Included)

Additional automation is performed using shell scripts (not included here) to:

- Launch large job batches  
- Monitor progress  
- Post-process CSV outputs  
- Organize results into datasets  

These scripts are simple wrappers around the Java programs described above.

---

## Dependencies

This code depends on:

- Java 11+
- `fastutil` library (`it.unimi.dsi:fastutil`)

---

## Purpose

This Java implementation is the primary tool used to generate the exact enumeration datasets published in this repository and archived via Zenodo.

All published data is a direct output of this code.

---

## Dense CSV Output Policy

All enumeration files produced by this project use a **dense CSV format**.

This means that **every** pair <img src="https://latex.codecogs.com/svg.latex?%28o%2Ca%29" /> with

<img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20o%20%5Cle%20rc%2C%20%5Cqquad%200%20%5Cle%20a%20%5Cle%202rc%20-%20r%20-%20c" />

appears explicitly in the output, including rows with `count = 0`.

### Example (dense)

```
r,c,o,a,count
5,8,0,0,1
5,8,0,1,0
5,8,0,2,0
...
5,8,40,67,1
.DONE.
```

Zero-count rows are **not omitted**.

### Rationale

Dense output is used because it:

- Eliminates ambiguity about missing <img src="https://latex.codecogs.com/svg.latex?%28o%2Ca%29" /> values  
- Simplifies verification and consistency checks  
- Preserves the full support structure of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />  
- Facilitates theoretical analysis of adjacency bounds  

Sparse (holey) CSV formats are **not used** in this repository.

### Verification

All data files are validated using the `verify_csv.py` script, which assumes:

- Dense output  
- A terminating `.DONE.` sentinel line  
- Exact combinatorial consistency:

<img src="https://latex.codecogs.com/svg.latex?%5Csum_%7Bo%2Ca%7D%20m%28r%2Cc%2Co%2Ca%29%20%3D%202%5E%7Brc%7D%2C%20%5Cqquad%0A%5Csum_a%20m%28r%2Cc%2Co%2Ca%29%20%3D%20%5Cbinom%7Brc%7D%7Bo%7D" />

