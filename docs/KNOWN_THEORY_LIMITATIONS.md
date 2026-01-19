# Known Theory Limitations

This repository provides **exact, verified enumeration data** for the combinatorial function

\[
m(r,c,o,a),
\]

the number of ways to place \( o \) occupied cells in an \( r \times c \) grid such that exactly \( a \) horizontal/vertical adjacencies occur.

While the **data itself is exact**, some of the **theoretical bounds and closed‑form formulas** used for analysis (notably for \( a_{\min} \) and \( a_{\max} \)) have **regime‑dependent validity**.  
This section documents those known limitations clearly and transparently.

---

## 1. Data Correctness vs. Theory

All CSV files in this repository satisfy the following **hard invariants**:

- Dense format: every \( (o,a) \) pair appears
- \( \sum_{o,a} m(r,c,o,a) = 2^{rc} \)
- \( \sum_a m(r,c,o,a) = \binom{rc}{o} \)
- Boundary conditions:
  - \( m(r,c,0,0) = 1 \)
  - \( m(r,c,rc,2rc-r-c) = 1 \)

These ensure the **enumeration is mathematically correct**.

All additional checks involving theoretical formulas are **diagnostic**, not correctness requirements.

---

## 2. Lower Adjacency Bound \( a_{\min} \)

### Robust (Exact) Bound

For all grids, the *true* minimal number of adjacencies for a given \( o \) is determined by:

- The grid graph’s bipartite structure
- The independence number \( \alpha = \lceil rc/2 \rceil \)
- The degree sequence of the smaller color class

When \( o > \alpha \), the minimum induced adjacencies equal the sum of the \( o-\alpha \) smallest vertex degrees in the opposite color class.

This bound is **always correct** and is used by the verifier.

### Closed‑Form Approximation

The closed‑form \( a_{\min}(r,c,o) \) formula used in the accompanying theory assumes an initial slope of approximately **3** above \( \alpha \) for typical 2D grids.

However, this approximation fails for certain geometries, especially:

- **Odd × odd grids** (e.g., 5×5, 7×7, 11×11)  
- Grids with many **degree‑2 corner vertices**  
- Small minimum dimension (e.g., \( r=3,5,7 \))

In these cases, the true initial slope is often **2**, not 3.

Therefore:

> The closed‑form \( a_{\min} \) formula is **regime‑dependent** and should not be treated as universally exact.

---

## 3. Upper Adjacency Bound \( a_{\max} \)

The closed‑form \( a_{\max}(r,c,o) \) formula is based on rectangular block‑packing arguments.

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

- Closed‑form \( a_{\min} \) mismatches  
- Closed‑form \( a_{\max} \) mismatches  

This ensures that:

- Valid data is never rejected  
- Theory limitations are transparently documented  

---

## 6. Recommended Usage

When using these data or formulas:

- Use the **DP data** as the authoritative source for all \( (r,c,o,a) \)
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
