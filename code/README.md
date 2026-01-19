# Java Dynamic Programming Enumerator for \( m(r,c,o,a) \)

This directory contains a Java implementation of an exact dynamic-programming (DP) algorithm for computing the combinatorial function

\[
m(r,c,o,a),
\]

the number of ways to place \( o \) occupied cells in an \( r \times c \) grid such that exactly \( a \) horizontal/vertical adjacencies occur.

The implementation is designed for **exact enumeration** using arbitrary-precision arithmetic and supports multi-threaded batch execution.

---

## Files

### `DP_optimized.java`

Core DP engine that:

- Implements a column-by-column (row-extension) dynamic program  
- Tracks:
  - Occupied cell count \( o \)  
  - Adjacency count \( a \)  
- Uses `BigInteger` for exact arithmetic  
- Outputs dense CSV tables with a `.DONE.` sentinel line  

Key features:

- Bitmask representation of column states  
- Horizontal and vertical adjacency tracking  
- Symmetry reduction: grids are transposed so that \( r \le c \)  
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

- Total occupied cells so far \( o \)
- Total adjacencies so far \( a \)

Transitions between consecutive columns account for:

- Horizontal adjacencies within the new column  
- Vertical adjacencies between old and new columns  

At the final column, all states are aggregated to produce the full table:

\[
m(r,c,o,a).
\]

All counts are **exact**.

---

## Computational Limits

Due to the exponential number of column states:

- The column height (\( r \)) is practically limited to **\( r \le 30 \)**  
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
- `count` = exact value of \( m(r,c,o,a) \)  

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

This means that **every** pair \( (o,a) \) with

\[
0 \le o \le rc, \qquad 0 \le a \le 2rc - r - c
\]

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

- Eliminates ambiguity about missing \( (o,a) \) values  
- Simplifies verification and consistency checks  
- Preserves the full support structure of \( m(r,c,o,a) \)  
- Facilitates theoretical analysis of adjacency bounds  

Sparse (holey) CSV formats are **not used** in this repository.

### Verification

All data files are validated using the `verify_csv.py` script, which assumes:

- Dense output  
- A terminating `.DONE.` sentinel line  
- Exact combinatorial consistency:

\[
\sum_{o,a} m(r,c,o,a) = 2^{rc}, \qquad
\sum_a m(r,c,o,a) = \binom{rc}{o}
\]

