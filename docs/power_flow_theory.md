# Newton-Raphson Power Flow — Theory & Background

## 1. Overview

The **power flow problem** (also called the load-flow problem) determines the
steady-state operating condition of an AC power network: bus voltages, phase
angles, and branch power flows given known generation schedules and load
demands.  It is the computational foundation of every Energy Management System
(EMS), planning study, and contingency analysis tool used in modern power
systems engineering.

The Newton-Raphson (N-R) method is the industry-standard solver.  It
reformulates the nonlinear power balance equations as a sequence of linearised
systems and iterates until the solution error (called the *mismatch*) falls
below a specified tolerance.  Compared to older Gauss-Seidel techniques, N-R
typically converges quadratically — requiring four to six iterations for
practical systems — and handles ill-conditioned networks far more robustly.

---

## 2. Bus Classification

Every bus in the network falls into one of three IEEE-standard categories:

| Type  | Also called     | Fixed quantities  | Solved quantities |
|-------|-----------------|-------------------|-------------------|
| Slack | Swing / Type 1  | \|V\|, δ (= 0°)   | P, Q              |
| PV    | Voltage-controlled / Type 2 | \|V\|, P | Q, δ  |
| PQ    | Load / Type 3   | P, Q              | \|V\|, δ          |

**Slack bus** — One bus must be designated the reference.  Its angle fixes the
global angle reference frame (δ = 0) and its real and reactive injections are
free to balance system losses; they are computed after convergence.  In
practice this is usually the largest generator bus.

**PV buses** — Generator buses where the terminal voltage is held constant by
the automatic voltage regulator (AVR).  The real power output P is scheduled;
the reactive output Q is the unknown.  Most systems include reactive capability
limits (Q_min, Q_max) which, if violated, cause the bus to switch to PQ type —
a procedure known as *PV-to-PQ switching* or *Q-limit enforcement*.

**PQ buses** — Load buses and passive junction buses.  Both P and Q are
scheduled (typically negative for loads, indicating consumption) and both
voltage magnitude and angle are unknowns.

---

## 3. Power Balance Equations

For a network with *n* buses, the complex power injected at bus *i* is:

```
S_i = P_i + jQ_i = V_i · Σ_j (Y_ij · V_j)*
```

Expanding into real and imaginary parts using polar form
`V_i = |V_i| ∠ δ_i`:

```
P_i = |V_i| Σ_j |V_j| (G_ij cos(δ_i − δ_j) + B_ij sin(δ_i − δ_j))

Q_i = |V_i| Σ_j |V_j| (G_ij sin(δ_i − δ_j) − B_ij cos(δ_i − δ_j))
```

where `G_ij = Re(Y_ij)` and `B_ij = Im(Y_ij)`.

The *mismatch* at each bus is the difference between the scheduled and
calculated injections:

```
ΔP_i = P_i^(sch) − P_i^(calc)
ΔQ_i = Q_i^(sch) − Q_i^(calc)
```

Convergence is declared when the L∞ norm (maximum absolute element) of the
combined mismatch vector falls below the specified tolerance, typically
10⁻⁶ pu on a 100 MVA base.

---

## 4. Newton-Raphson Iteration

Each iteration solves the linearised system:

```
[ ΔP ]   [ H   N ] [ Δδ      ]
[ ΔQ ] = [ J'  L ] [ ΔV / V  ]
```

The **Jacobian** is partitioned into four sub-matrices evaluated at the
current operating point:

| Submatrix | Element (i ≠ j)                                       | Diagonal element                                       |
|-----------|-------------------------------------------------------|--------------------------------------------------------|
| H[i,j]   | `V_i V_j (G_ij sin θ_ij − B_ij cos θ_ij)`           | `−Q_i − B_ii V_i²`                                    |
| N[i,j]   | `V_i V_j (G_ij cos θ_ij + B_ij sin θ_ij)`           | `P_i + G_ii V_i²`                                     |
| J'[i,j]  | `−V_i V_j (G_ij cos θ_ij + B_ij sin θ_ij)`          | `P_i − G_ii V_i²`                                     |
| L[i,j]   | `V_i V_j (G_ij sin θ_ij − B_ij cos θ_ij)`           | `Q_i − B_ii V_i²`                                     |

where `θ_ij = δ_i − δ_j`.

The dimension of the Jacobian is `(n_pq + n_pv + n_pq) × (n_pq + n_pv + n_pq)`
— equivalently, `(2·n_pq + n_pv) × (2·n_pq + n_pv)`.  The slack bus rows and
columns are always excluded; PV buses contribute only to the ΔP / Δδ
partitions, not the ΔQ / ΔV ones.

---

## 5. Flat Start

A *flat start* initialises all unknown voltages to 1∠0° pu — a uniform,
"flat" profile.  This is the standard starting point for transmission-level
power flow studies because:

1. The network is typically near 1 pu voltage under normal loading.
2. Flat start places the initial iterate in the attraction basin of the
   high-voltage (operable) solution.
3. The Jacobian at flat start is well-conditioned for typical networks.

For heavily loaded systems or unusual topologies, a warm start using results
from a prior solved case (e.g. the previous dispatch interval) reduces iteration
count and improves robustness.

---

## 6. Convergence Properties

Newton-Raphson exhibits **quadratic convergence** near the solution: once the
mismatch drops below roughly 10⁻² pu, each subsequent iteration approximately
squares the error.  Practical four-to-six iteration convergence is the norm for
well-conditioned transmission systems.

Convergence can fail or slow when:

- The network is at or near its **maximum loadability** (nose-point of the P-V
  curve), where the Jacobian becomes singular.
- There are **very weak buses** connected only through high-impedance paths.
- **Isolated islands** create a singular Y-bus.
- **Q-limit violations** on multiple PV buses cause repeated bus-type switching,
  inducing oscillation.

Practical mitigations include step-size damping (μ factor applied to dx),
reactive power control enforcement, and automatic bus-type switching logic.

---

## 7. Per-Unit Normalisation

All calculations are performed in the **per-unit (pu) system** on a chosen
MVA and kV base (typically 100 MVA).  Per-unit quantities are dimensionless
ratios to the base:

```
Z_pu = Z_ohm / Z_base        Z_base = kV_base² / MVA_base
V_pu = V_kV / kV_base        S_pu = S_MVA / MVA_base
```

Per-unit normalisation removes the need to track transformer turns ratios in
the bulk of the calculation and makes the magnitudes of all quantities
comparable across voltage levels.

---

## 8. Practical Engineering Tips

1. **Tolerance selection** — 10⁻⁶ pu on a 100 MVA base corresponds to
   approximately 0.1 W resolution — far below any metering uncertainty.  For
   real-time EMS applications, 10⁻⁴ pu is often sufficient and faster.

2. **Sparse factorisation** — For large systems (thousands of buses), store the
   Y-bus and Jacobian as sparse matrices and use sparse LU decomposition
   (e.g. `scipy.sparse.linalg.spsolve`).  Dense factorisation scales as O(n³)
   and becomes impractical above ~500 buses.

3. **Decoupled methods** — The fast-decoupled (FDPF) method exploits the weak
   coupling between P/δ and Q/V in high-voltage transmission networks,
   reducing each iteration to two smaller matrix solves.  It trades some
   robustness for speed, with roughly 2–3× fewer floating-point operations per
   iteration.

4. **Initialisation for meshed networks** — Bus types must be consistent:
   exactly one slack bus, PV buses only for controllable voltage sources.  An
   improperly specified slack leads to a singular Jacobian.

5. **IEEE test systems** — Validate solver implementations against published
   results for the IEEE 14-, 30-, 57-, and 118-bus systems.  Reference bus
   voltages and angles are widely available and serve as regression benchmarks
   (IEEE PES Power Systems Test Case Archive).

---

## References

- Glover, J. D., Sarma, M. S., & Overbye, T. J. (2022). *Power System Analysis
  and Design*, 6th ed. Cengage Learning.
- Stott, B. (1974). Review of load-flow calculation methods. *Proceedings of
  the IEEE*, 62(7), 916–929.
- Bergen, A. R., & Vittal, V. (2000). *Power Systems Analysis*, 2nd ed.
  Prentice Hall.
- IEEE Std 399-1997, *IEEE Recommended Practice for Industrial and Commercial
  Power Systems Analysis (Brown Book)*.
