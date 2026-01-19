# Verification Methodology

This repository provides **exact enumeration data** for the combinatorial function

<img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />

the number of ways to place o occupied cells in an <img src="https://latex.codecogs.com/svg.latex?r%20%5Ctimes%20c" /> grid such that exactly <img src="https://latex.codecogs.com/svg.latex?a" /> horizontal/vertical adjacencies occur.

To ensure correctness, all data files are subjected to a strict, reproducible **verification pipeline**.  
This document describes the methodology used to validate every CSV file in the dataset.

---

## 1. Scope of Verification

The verification process focuses on **data integrity**, not on enforcing theoretical conjectures.

Specifically, it checks that each file:

- Represents a complete enumeration of all <img src="https://latex.codecogs.com/svg.latex?2%5E%7Brc%7D" /> subsets  
- Uses a consistent and documented CSV format  
- Satisfies core combinatorial identities  
- Contains no malformed, missing, or corrupted entries  

Theoretical bounds (such as closed-form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D" /> and <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D" />) are treated as **diagnostic tools**, not correctness requirements.

---

## 2. Input Format Requirements

Each data file must satisfy:

### CSV Structure

```
r,c,o,a,count
...
.DONE.
```

Where:

- `r`, `c` — grid dimensions  
- `o` — number of occupied cells  
- `a` — number of adjacencies  
- `count` — exact value of <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Co%2Ca%29" />  

### Dense Format

All files are **dense**:

- Every <img src="https://latex.codecogs.com/svg.latex?%28o%2Ca%29" /> pair appears  
- Zero-count rows are included  
- No rows are omitted  

### Sentinel

The final line must be:

```
.DONE.
```

This marks successful completion of the enumeration job.

---

## 3. Hard Invariants (Data Correctness)

Each CSV file is checked against the following **hard invariants**.

Failure of any of these indicates a **corrupted or incomplete dataset**.

### 3.1 Grid Consistency

All rows must have identical `r` and `c` values.

---

### 3.2 Valid Ranges

Each row must satisfy:

<img src="https://latex.codecogs.com/svg.latex?0%20%5Cle%20o%20%5Cle%20rc%2C%20%5Cqquad%0A0%20%5Cle%20a%20%5Cle%202rc%20-%20r%20-%20c%2C%20%5Cqquad%0Acount%20%5Cge%200." />

---

### 3.3 Dense Shape

The total number of data rows must equal:

<img src="https://latex.codecogs.com/svg.latex?%28rc%20%2B%201%29%282rc%20-%20r%20-%20c%20%2B%201%29." />

---

### 3.4 Total Count

The sum of all counts must satisfy:

<img src="https://latex.codecogs.com/svg.latex?%5Csum_%7Bo%2Ca%7D%20m%28r%2Cc%2Co%2Ca%29%20%3D%202%5E%7Brc%7D." />

This confirms that **every subset of grid cells** is counted exactly once.

---

### 3.5 Per-Occupancy Sums

For each o, the data must satisfy:

<img src="https://latex.codecogs.com/svg.latex?%5Csum_a%20m%28r%2Cc%2Co%2Ca%29%20%3D%20%5Cbinom%7Brc%7D%7Bo%7D." />

This ensures that all subsets of size o are correctly enumerated.

---

### 3.6 Boundary Conditions

The extreme configurations must be present:

- Empty grid:
  <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2C0%2C0%29%20%3D%201" />
- Fully occupied grid:
  <img src="https://latex.codecogs.com/svg.latex?m%28r%2Cc%2Crc%2C2rc%20-%20r%20-%20c%29%20%3D%201" />

---

## 4. Verification Tools

All checks are implemented in the script:

```
code/verify_csv.py
```

Batch verification across the entire dataset is performed using:

```
code/verify_batch.py
```

These scripts:

- Enforce all hard invariants  
- Reject malformed or incomplete files  
- Report (but do not fail on) theory mismatches  

---

## 5. Theoretical Diagnostics (Non-Fatal)

In addition to data integrity checks, the verifier reports:

- Differences between closed-form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmin%7D%28r%2Cc%2Co%29" /> and the true bipartite lower bound  
- Differences between closed-form <img src="https://latex.codecogs.com/svg.latex?a_%7B%5Cmax%7D%28r%2Cc%2Co%29" /> and observed support  

These diagnostics:

- Identify regime-dependent limitations of theoretical formulas  
- Do **not** indicate data errors  
- Are documented in `KNOWN_THEORY_LIMITATIONS.md`  

---

## 6. Failure Handling

If a file fails verification, it is typically due to:

- Truncated output (job interruption)  
- Missing rows  
- Corrupted sentinel  
- Incomplete enumeration  

Such files are **re-generated** using the Java DP code.

No manual patching is performed.

---

## 7. Reproducibility

The verification process is:

- Deterministic  
- Scripted  
- Independent of theoretical assumptions  

This ensures that:

- All published data is reproducible  
- Errors are detectable  
- Dataset integrity can be independently confirmed  

---

## 8. Summary

The verification methodology guarantees that:

- Every CSV file represents a complete and correct enumeration  
- All combinatorial identities are satisfied  
- Theory limitations are transparently documented  
- Users can trust the dataset as an exact reference  

---
