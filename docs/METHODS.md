# Methods: Exact Enumeration of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />

## Problem Definition

Let <img src="https://latex.codecogs.com/svg.latex?G_%7Br%2Cc%7D" /> denote the r × c rectangular grid graph, whose vertices correspond to grid cells and whose edges represent horizontal and vertical adjacencies.

For integers

- <img src="https://latex.codecogs.com/svg.latex?r%2C%20c%20%5Cge%201" /> (grid dimensions),  
- <img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20o%20%5Cle%20rc" /> (number of occupied cells),  
- <img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20a%20%5Cle%202rc%20-%20r%20-%20c" /> (number of adjacencies),  

the quantity <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" /> is defined as the number of subsets of o vertices of <img src="https://latex.codecogs.com/svg.latex?G_%7Br%2Cc%7D" /> whose induced subgraph contains exactly a edges.

Boundary conditions:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2C0%2C0%29%20%3D%201%2C%20%5Cqquad%0Am%28r%2Cc%2Crc%2C2rc-r-c%29%20%3D%201." />

Symmetry:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%20%3D%20m%28c%2Cr%2Co%2Ca%29." />

---

## Overview of the Enumeration Algorithm

All values of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" /> were computed using an exact dynamic programming (DP) algorithm that processes the grid column by column.

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

Each column of height <img src="https://latex.codecogs.com/svg.latex?r" /> is represented by a bitmask <img src="https://latex.codecogs.com/svg.latex?s%20%5Cin%20%5C%7B0%2C1%5C%7D%5Er" />, where:

- Bit <img src="https://latex.codecogs.com/svg.latex?i%20%3D%201" /> indicates that the <img src="https://latex.codecogs.com/svg.latex?i" />-th cell in the column is occupied.
- Bit <img src="https://latex.codecogs.com/svg.latex?i%20%3D%200" /> indicates that the cell is empty.

For a given column state <img src="https://latex.codecogs.com/svg.latex?s" />, we define:

- <img src="https://latex.codecogs.com/svg.latex?%5Cmathrm%7Bpopcount%7D%28s%29" />: number of occupied cells in the column.  
- <img src="https://latex.codecogs.com/svg.latex?h%28s%29" />: number of horizontal adjacencies within the column (i.e., adjacent occupied vertical pairs).  

---

## Dynamic Programming Transitions

Let <img src="https://latex.codecogs.com/svg.latex?s" /> and <img src="https://latex.codecogs.com/svg.latex?t" /> be the bitmask states of two consecutive columns.

The number of vertical adjacencies formed between them is:

<img src="https://latex.codecogs.com/svg.latex?v%28s%2Ct%29%20%3D%20%5Cmathrm%7Bpopcount%7D%28s%20%5Cwedge%20t%29." />

The DP transition from state <img src="https://latex.codecogs.com/svg.latex?s" /> to <img src="https://latex.codecogs.com/svg.latex?t" /> updates:

- Occupancy count:  
  <img src="https://latex.codecogs.com/svg.latex?o%20%5Cleftarrow%20o%20%2B%20%5Cmathrm%7Bpopcount%7D%28t%29" />

- Adjacency count:  
  <img src="https://latex.codecogs.com/svg.latex?a%20%5Cleftarrow%20a%20%2B%20h%28t%29%20%2B%20v%28s%2Ct%29" />

Each transition contributes multiplicatively to the total count of configurations realizing the updated <img src="https://latex.codecogs.com/svg.latex?%28o%2Ca%29" /> pair.

---

## DP Table Structure

For each column index <img src="https://latex.codecogs.com/svg.latex?k%20%5Cin%20%5C%7B1%2C%5Cdots%2Cc%5C%7D" />, the algorithm maintains a table:

<img src="https://latex.codecogs.com/svg.latex?D_k%5Bs%5D%5Bo%5D%5Ba%5D%2C" />

which stores the number of partial configurations ending in column state <img src="https://latex.codecogs.com/svg.latex?s" /> with:

- o occupied cells so far,  
- a adjacencies so far.  

Initialization:

<img src="https://latex.codecogs.com/svg.latex?D_0%5B0%5D%5B0%5D%5B0%5D%20%3D%201." />

Final aggregation:

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%20%3D%20%5Csum_s%20D_c%5Bs%5D%5Bo%5D%5Ba%5D." />

---

## Symmetry Reduction

Since

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29%20%3D%20m%28c%2Cr%2Co%2Ca%29%2C" />

all computations are performed with <img src="https://latex.codecogs.com/svg.latex?r%20%5Cle%20c" /> by transposing the grid if necessary.  
This reduces the maximum column height and improves performance.

---

## Exactness and Arithmetic

All computations use exact integer arithmetic (arbitrary precision).  
No floating-point approximations, Monte Carlo methods, or heuristic pruning are employed.

Thus, all reported values of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" /> are exact.

---

## Computational Scope

The algorithm exhaustively enumerates:

- All <img src="https://latex.codecogs.com/svg.latex?2%5Er" /> column states.  
- All <img src="https://latex.codecogs.com/svg.latex?2%5Er%20%5Ctimes%202%5Er" /> column transitions.  
- All valid <img src="https://latex.codecogs.com/svg.latex?%28o%2Ca%29" /> combinations for each grid size.

The total runtime grows exponentially with <img src="https://latex.codecogs.com/svg.latex?r" />, so enumerations are currently limited to moderate grid heights, while allowing large widths <img src="https://latex.codecogs.com/svg.latex?c" />.

---

## Reproducibility

The implementation:

- Uses deterministic DP transitions.  
- Produces identical results across runs.  
- Is documented in the associated code repository.  

All datasets released are direct outputs of this algorithm with no post-processing other than formatting into CSV files.

---

## Summary

The values of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" /> provided in this dataset were computed using an exact, column-based dynamic programming algorithm that:

- Enumerates all valid grid configurations,  
- Tracks occupancy and adjacency counts exactly,  
- Uses symmetry to reduce computational cost,  
- Produces mathematically exact results suitable for verification and analysis.
