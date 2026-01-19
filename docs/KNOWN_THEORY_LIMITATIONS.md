# Known Theory Limitations

This repository provides **exact, verified enumeration data** for the combinatorial function

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />

the number of ways to place  o  occupied cells in an  r \times c  grid such that exactly  a  horizontal/vertical adjacencies occur.

While the **data itself is exact**, some of the **theoretical bounds and closed‑form formulas** used for analysis (notably for <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" /> and <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D" />) have **regime‑dependent validity**.  
This section documents those known limitations clearly and transparently.

---

## 1. Data Correctness vs. Theory

All CSV files in this repository satisfy the following **hard invariants**:

- Dense format: every  (o,a)  pair appears
- <img src="https://latex.codecogs.com/svg.latex?%5Csum_%7Bo%2Ca%7D%20m%28r%2Cc%2Co%2Ca%29%3D2%5E%7Brc%7D" />
- <img src="https://latex.codecogs.com/svg.latex?%5Csum_a%20m%28r%2Cc%2Co%2Ca%29%3D%5Cbinom%7Brc%7D%7Bo%7D" />
- Boundary conditions:
  - <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2C0%2C0%29%3D1" />
  - <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Crc%2C2rc-r-c%29%3D1" />

These ensure the **enumeration is mathematically correct**.

All additional checks involving theoretical formulas are **diagnostic**, not correctness requirements.

---

## 2. Lower Adjacency Bound <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" />

### Robust (Exact) Bound

For all grids, the *true* minimal number of adjacencies for a given  o  is determined by:

- The grid graph’s bipartite structure
- The independence number <img src="https://latex.codecogs.com/svg.latex?%5Calpha%3D%5Clceil%20rc/2%20%5Crceil" />
- The degree sequence of the smaller color class

When <img src="https://latex.codecogs.com/svg.latex?o%3E%5Calpha" />, the minimum induced adjacencies equal the sum of the <img src="https://latex.codecogs.com/svg.latex?o-%5Calpha" /> smallest vertex degrees in the opposite color class.

This bound is **always correct** and is used by the verifier.

### Closed‑Form Approximation

The closed‑form  <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" />(r,c,o)  formula used in the accompanying theory assumes an initial slope of approximately **3** above  <img src="https://latex.codecogs.com/svg.latex?%5Calpha" />  for typical 2D grids.

However, this approximation fails for certain geometries, especially:

- **Odd × odd grids** (e.g., 5×5, 7×7, 11×11)  
- Grids with many **degree‑2 corner vertices**  
- Small minimum dimension (e.g., r=3,5,7)

In these cases, the true initial slope is often **2**, not 3.

Therefore:

> The closed‑form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" /> formula is **regime‑dependent** and should not be treated as universally exact.

---

## 3. Upper Adjacency Bound <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D" />

The closed‑form  <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D" />(r,c,o)  formula is based on rectangular block‑packing arguments.

It is accurate for most large, “bulk” 2D grids, but mismatches occur for:

- **Odd × odd grids**
- Small or narrow grids
- Boundary‑dominated geometries

These mismatches do **not** indicate errors in the data.  
They indicate that the packing model does not capture all valid configurations for those grid shapes.

---

## 4. Why These Limitations Exist

The theoretical formulas were designed to describe:

- Large, interior‑dominated grids
- Typical adjacency growth regimes
- Asymptotic behavior

They were **not** intended to fully capture:

- Corner‑dominated configurations  
- Small grids  
- Strong parity effects  
- Boundary‑optimized constructions  

The exact DP data in this repository provides the empirical ground truth for these regimes.

---

## 5. How the Verifier Handles This

The verification scripts enforce **data correctness only**:

- Structural integrity
- Combinatorial totals
- Boundary conditions

The following are treated as **non‑fatal diagnostics**:

- Closed‑form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" /> mismatches  
- Closed‑form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D" /> mismatches  

This ensures that:

- Valid data is never rejected  
- Theory limitations are transparently documented  

---

## 6. Recommended Usage

When using these data or formulas:

- Use the **DP data** as the authoritative source for all  (r,c,o,a) 
- Treat closed‑form bounds as **approximations**
- State grid‑size restrictions explicitly in any theoretical claims
- Avoid applying formulas to odd×odd or very small grids without qualification

---

## 7. Scientific Integrity Statement

This repository intentionally separates:

- **Exact enumeration** (guaranteed correct)
- **Theoretical models** (regime‑dependent)

All known limitations are documented openly to ensure transparency, reproducibility, and correct interpretation of results.

---
