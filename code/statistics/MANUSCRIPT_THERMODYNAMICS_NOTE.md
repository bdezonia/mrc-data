# Proposed methods addition for MRC paper (not yet applied to manuscript)

## Canonical finite-size lattice-gas observables

On an open rectangular lattice with `N=rc` sites and fixed occupancy `o`, take
`H(S)=-J a(S)`, where `a(S)` is the number of occupied orthogonal nearest-neighbor
pairs in configuration `S`. The MRC table provides the degeneracy of each energy
level, because `H(S)` depends only on `a(S)`. Write `K = beta J`. Then

`Z_{r,c,o}(K) = sum_a m(r,c,o,a) exp(K a)`.

The exact canonical distribution of the coupling statistic is

`Pr_K(A=a) = m(r,c,o,a) exp(K a) / Z_{r,c,o}(K)`.

Differentiation gives `d(log Z)/dK = E_K[A]` and
`d^2(log Z)/dK^2 = Var_K(A)`, which is nonnegative. At fixed `J`, the mean
interaction energy is `E_K[H] = -J E_K[A]`; the heat capacity is
`C_V/k_B = K^2 Var_K(A)`.

At `K=0`, `Z_{r,c,o}(0)=binom(rc,o)`, recovering the uniform fixed-occupancy
null distribution used by the original statistical calculator. The computation
is an exact finite sum over integer degeneracies, evaluated numerically using
arbitrary-precision decimal arithmetic and a shifted exponential sum. No
thermodynamic-limit approximation or Monte Carlo sampling is involved.

### Worked 2x2 example

For `r=c=2` and `o=2`, there are six configurations: two have no contact and
four have one contact. Thus `Z_{2,2,2}(K) = 2 + 4 exp(K)` and
`E_K[A] = 4 exp(K) / (2+4 exp(K))`; `Var_K(A) = p_K(1-p_K)` with
`p_K=E_K[A]`. The included software reproduces this finite analytical result.

### Boundaries and limitations

These statements require an open rectangular lattice, identical sites, a fixed
number of particles, and a Hamiltonian with only uniform occupied-pair energy.
They do not directly apply to periodic models, heterogeneous interactions,
long-range energies, or grand-canonical ensembles. The data archive is exact
within its completed rectangle domain, not an arbitrary-size solver.
