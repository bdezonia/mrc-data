# Methods: Exact Enumeration of \( m(r,c,o,a) \)

## Problem Definition

Let \( G_{r,c} \) denote the \( r \times c \) rectangular grid graph, whose vertices correspond to grid cells and whose edges represent horizontal and vertical adjacencies.

For integers

- \( r, c \ge 1 \) (grid dimensions),  
- \( 0 \le o \le rc \) (number of occupied cells),  
- \( 0 \le a \le 2rc - r - c \) (number of adjacencies),  

the quantity \( m(r,c,o,a) \) is defined as the number of subsets of \( o \) vertices of \( G_{r,c} \) whose induced subgraph contains exactly \( a \) edges.

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

## Overview of the Enumeration Algorithm

All values of \( m(r,c,o,a) \) were computed using an exact dynamic programming (DP) algorithm that processes the grid column by column.

The algorithm maintains a state representation for each column that encodes:

1. Which cells in the current column are occupied.  
2. The number of occupied cells selected so far.  
3. The number of adjacency edges formed so far.  

Transitions between states account for:

- Horizontal adjacencies within a column.  
- Vertical adjacencies between consecutive columns.  

Counts are accumulated exactly using arbitrary-precision integer arithmetic.

---

## Column State Representation

Each column of height \( r \) is represented by a bitmask \( s \in \{0,1\}^r \), where:

- Bit \( i = 1 \) indicates that the \( i \)-th cell in the column is occupied.
- Bit \( i = 0 \) indicates that the cell is empty.

For a given column state \( s \), we define:

- \( \mathrm{popcount}(s) \): number of occupied cells in the column.  
- \( h(s) \): number of horizontal adjacencies within the column (i.e., adjacent occupied vertical pairs).  

---

## Dynamic Programming Transitions

Let \( s \) and \( t \) be the bitmask states of two consecutive columns.

The number of vertical adjacencies formed between them is:

\[
v(s,t) = \mathrm{popcount}(s \wedge t).
\]

The DP transition from state \( s \) to \( t \) updates:

- Occupancy count:  
  \[
  o \leftarrow o + \mathrm{popcount}(t)
  \]

- Adjacency count:  
  \[
  a \leftarrow a + h(t) + v(s,t)
  \]

Each transition contributes multiplicatively to the total count of configurations realizing the updated \( (o,a) \) pair.

---

## DP Table Structure

For each column index \( k \in \{1,\dots,c\} \), the algorithm maintains a table:

\[
D_k[s][o][a],
\]

which stores the number of partial configurations ending in column state \( s \) with:

- \( o \) occupied cells so far,  
- \( a \) adjacencies so far.  

Initialization:

\[
D_0[0][0][0] = 1.
\]

Final aggregation:

\[
m(r,c,o,a) = \sum_s D_c[s][o][a].
\]

---

## Symmetry Reduction

Since

\[
m(r,c,o,a) = m(c,r,o,a),
\]

all computations are performed with \( r \le c \) by transposing the grid if necessary.  
This reduces the maximum column height and improves performance.

---

## Exactness and Arithmetic

All computations use exact integer arithmetic (arbitrary precision).  
No floating-point approximations, Monte Carlo methods, or heuristic pruning are employed.

Thus, all reported values of \( m(r,c,o,a) \) are exact.

---

## Computational Scope

The algorithm exhaustively enumerates:

- All \( 2^r \) column states.  
- All \( 2^r \times 2^r \) column transitions.  
- All valid \( (o,a) \) combinations for each grid size.

The total runtime grows exponentially with \( r \), so enumerations are currently limited to moderate grid heights, while allowing large widths \( c \).

---

## Reproducibility

The implementation:

- Uses deterministic DP transitions.  
- Produces identical results across runs.  
- Is documented in the associated code repository.  

All datasets released are direct outputs of this algorithm with no post-processing other than formatting into CSV files.

---

## Summary

The values of \( m(r,c,o,a) \) provided in this dataset were computed using an exact, column-based dynamic programming algorithm that:

- Enumerates all valid grid configurations,  
- Tracks occupancy and adjacency counts exactly,  
- Uses symmetry to reduce computational cost,  
- Produces mathematically exact results suitable for verification and analysis.
