# Fault Analysis Guide

## 1. Introduction

A **short-circuit fault** is an abnormal low-impedance connection between
conductors that causes currents far exceeding normal operating values.  Accurate
fault analysis is essential for:

- Selecting circuit breakers with adequate interrupting rating (IEEE C37 series).
- Setting protective relay pickup levels and time-delay coordination.
- Designing grounding systems to limit touch and step potentials.
- Verifying substation equipment withstand ratings.

This guide covers the two most commonly studied fault types — the **balanced
three-phase fault** and the **single-line-to-ground (SLG) fault** — using the
Z-bus (impedance matrix) method and the theory of symmetrical components.

---

## 2. The Z-Bus Method

The **bus impedance matrix** Z_bus is the inverse of the Y-bus:

```
Z_bus = Y_bus⁻¹
```

The diagonal element `Z_kk` is the **Thevenin impedance** seen looking into
the network from bus *k*.  This is the key quantity needed for fault
calculations.

The Z-bus method assumes:

1. All generators are replaced by their internal voltage sources in series with
   their subtransient reactances (X″_d).
2. All pre-fault voltages are assumed to be 1∠0° pu (the flat-start condition
   is a good approximation for transmission-level studies).
3. Loads are neglected during the fault (conservative — loads limit fault
   currents slightly).

---

## 3. Symmetrical Components

Unbalanced faults (SLG, line-to-line, double-line-to-ground) produce
unbalanced three-phase currents and voltages.  **Fortescue's theorem**
(1918) shows that any unbalanced set of three-phase phasors can be decomposed
into three balanced **sequence components**:

| Sequence | Symbol | Phase rotation |
|----------|--------|----------------|
| Positive | (1)    | abc (normal rotation) |
| Negative | (2)    | acb (reversed rotation) |
| Zero     | (0)    | In-phase (common-mode) |

The transformation from phase to sequence quantities is:

```
[ V_a^(0) ]   [ 1  1   1  ] [ V_a ]
[ V_a^(1) ] = 1/3 [ 1  a   a² ] [ V_b ]
[ V_a^(2) ]   [ 1  a²  a  ] [ V_c ]
```

where `a = e^(j2π/3) = 1∠120°`.

Each sequence has its own network: the **positive-sequence network** reflects
normal load-flow topology; the **negative-sequence network** is identical for
static network elements (lines, transformers) but differs for generators;
the **zero-sequence network** depends strongly on transformer winding
connections and neutral grounding.

---

## 4. Three-Phase (Balanced) Fault

A three-phase bolted fault at bus *k* is the most severe fault type and is
balanced — it does not require sequence networks.

### Fault Current

```
I_f = V_k^(0) / (Z_kk + Z_f)
```

where:
- `V_k^(0)` = pre-fault voltage at bus *k* (typically 1.0 pu)
- `Z_kk` = Thevenin impedance from Z_bus diagonal
- `Z_f` = fault impedance (0 for bolted fault)

### Bus Voltages During Fault

The voltage at every bus drops during the fault:

```
V_i^(fault) = V_i^(0) − Z_ik · I_f
```

This voltage profile is used to determine relay operating quantities and to
assess which loads lose voltage support.

### Example Calculation

Given a 9-bus system with Z_55 = j0.1402 pu (Thevenin impedance at bus 5):

```
I_f = 1.0 / j0.1402 = −j7.13 pu  (magnitude 7.13 pu)

On 100 MVA, 230 kV base:  I_base = 100 / (√3 × 230) = 0.2510 kA
I_fault = 7.13 × 0.2510 = 1.79 kA
```

---

## 5. Single-Line-to-Ground (SLG) Fault

An SLG fault on phase A at bus *k* requires all three sequence networks
connected in series.

### Sequence Fault Current

```
I_a^(1) = V_k^(0) / (Z_1,kk + Z_2,kk + Z_0,kk + 3·Z_f)
```

By symmetry: `I_a^(1) = I_a^(2) = I_a^(0)`

### Phase-A Fault Current

```
I_a = 3 · I_a^(1)
```

Phases B and C carry no fault current in a pure SLG fault.

### Bus Voltages During SLG Fault

Positive-sequence bus voltages:
```
V_i^(1) = V_i^(0) − Z_1,ik · I_a^(1)
```

Negative-sequence bus voltages:
```
V_i^(2) = −Z_2,ik · I_a^(2)
```

Zero-sequence bus voltages:
```
V_i^(0) = −Z_0,ik · I_a^(0)
```

Phase voltages are reconstructed from the inverse sequence transformation.

### Example Calculation

Assume the positive and negative sequence Thevenin impedances at bus 5 are
both `j0.1402 pu`, and the zero-sequence impedance is `j0.0505 pu`:

```
I_a^(1) = 1.0 / (j0.1402 + j0.1402 + j0.0505 + 0)
        = 1.0 / j0.3309
        = −j3.022 pu

I_a (phase A) = 3 × 3.022 = 9.07 pu
```

SLG faults can produce higher ground fault currents than three-phase faults
when the zero-sequence impedance is low (e.g. solidly grounded systems with
many transformers in a delta-wye configuration).

---

## 6. Other Fault Types

While this toolkit currently implements three-phase and SLG faults, the
same Z-bus framework extends to:

| Fault Type               | Series connection of sequences |
|--------------------------|-------------------------------|
| Line-to-Line (LL)        | Z_1 and Z_2 in series, Z_0 open |
| Double-Line-to-Ground (DLG) | Z_1 in series with (Z_2 ‖ (Z_0 + 3Z_f)) |
| Open-Conductor (series fault) | Requires admittance matrix approach |

---

## 7. Zero-Sequence Network Construction

The zero-sequence network topology differs from the positive-sequence
network based on transformer winding connections:

| Transformer connection  | Zero-sequence path    |
|-------------------------|-----------------------|
| Wye-grounded / Wye-grounded | Through both windings |
| Wye-grounded / Delta    | Circulates in delta; isolated on other side |
| Delta / Delta           | Isolated (open circuit for zero sequence) |
| Wye-ungrounded / any   | Open circuit (no zero-sequence path) |

Incorrect zero-sequence network modelling is the most common source of
error in SLG fault calculations.

---

## 8. Fault MVA and Equipment Ratings

The **fault MVA** (short-circuit MVA) is a convenient quantity for equipment
selection:

```
Fault MVA = √3 · V_LL (kV) · I_fault (kA)
          = S_base (MVA) / |Z_kk (pu)|
```

Circuit breakers are rated by their **symmetrical interrupting current** (kA
rms) and must be able to interrupt the fault current within their rated number
of cycles.  The **DC offset** (asymmetrical component) decays with time
constant `L/R = X/(ωR)` and must also be considered for the first half-cycle
making current.

Per IEEE C37.010, the **closing and latching current** (peak asymmetrical) can
be estimated as `2.7 × I_sym` for X/R ratios typical of EHV systems.

---

## 9. References

- Glover, J. D., Sarma, M. S., & Overbye, T. J. (2022). *Power System Analysis
  and Design*, 6th ed. Cengage Learning. Chapters 9–10.
- Anderson, P. M. (1995). *Analysis of Faulted Power Systems*. IEEE Press.
- Fortescue, C. L. (1918). Method of symmetrical co-ordinates applied to the
  solution of polyphase networks. *AIEE Transactions*, 37(2), 1027–1140.
- IEEE Std C37.010-2016, *Application Guide for AC High-Voltage Circuit
  Breakers Rated on a Symmetrical Current Basis*.
- IEEE Std 141-1993, *IEEE Recommended Practice for Electric Power Distribution
  for Industrial Plants (Red Book)*.
