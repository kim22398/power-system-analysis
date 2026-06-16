# Power System Analysis Toolkit

[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-green?logo=pytest)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?logo=numpy&logoColor=white)](https://numpy.org/)

A professional-grade Python toolkit for steady-state power system analysis.
Implements foundational algorithms used in modern Energy Management Systems
(EMS) and power flow study software — built for engineers who need reliable,
readable, and extensible code.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Theory & Background](#theory--background)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Engineering Background](#engineering-background)
- [Running Tests](#running-tests)
- [Documentation](#documentation)
- [License](#license)

---

## Features

| Module | Description |
|---|---|
| `power_system/bus.py` | `Bus` dataclass — PQ / PV / Slack types, voltage phasors, Q limits |
| `power_system/line.py` | `Line` π-equivalent model with tap ratio and phase shift |
| `power_system/ybus.py` | Y-bus / Z-bus construction for arbitrary topologies |
| `power_system/power_flow.py` | Full Newton-Raphson solver (polar form, Jacobian sub-matrices) |
| `power_system/fault.py` | Three-phase and SLG fault analysis via symmetrical components |
| `power_system/losses.py` | Per-branch and system-total transmission loss computation |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/your-username/power-system-analysis.git
cd power-system-analysis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

No additional build step is required — the package is pure Python.

### 2. Run the IEEE 9-Bus Example

```bash
python examples/ieee_9bus.py
```

### 3. Run Tests

```bash
pytest tests/ -v
```

For a full step-by-step walkthrough see [docs/getting_started.md](docs/getting_started.md).

---

## Project Structure

```
power-system-analysis/
├── power_system/
│   ├── __init__.py         # Package exports: Bus, Line, build_ybus, NewtonRaphson, …
│   ├── bus.py              # Bus dataclass — voltage, type, scheduled injections, Q limits
│   ├── line.py             # Line π-model — R, X, B, tap ratio, phase shift, ratings
│   ├── ybus.py             # build_ybus() and ybus_to_zbus() — admittance/impedance matrices
│   ├── power_flow.py       # NewtonRaphson solver + PowerFlowResult container
│   ├── fault.py            # FaultAnalysis — 3-phase and SLG faults via Z-bus method
│   └── losses.py           # compute_losses() — per-branch and system-total MW/MVAR losses
├── examples/
│   └── ieee_9bus.py        # WSCC 9-bus test system: power flow, line flows, losses
├── tests/
│   └── test_ybus.py        # Pytest unit tests for Y-bus construction and Z-bus inversion
├── docs/
│   ├── getting_started.md  # Step-by-step install and first-run tutorial
│   ├── power_flow_theory.md # Newton-Raphson math: Jacobian, mismatch, bus types, tips
│   ├── fault_analysis_guide.md # Z-bus fault method, symmetrical components, examples
│   └── api_reference.md    # Full API docs for every class, method, and function
├── requirements.txt        # numpy, scipy, pandas, matplotlib, pytest
└── README.md
```

---

## Theory & Background

### Newton-Raphson Power Flow

The Newton-Raphson method solves the nonlinear AC power balance equations by
iterating on a linearised system at each step.  The **polar form** of the power
equations is used:

```
P_i = |V_i| Σ_j |V_j| (G_ij cos(δ_i − δ_j) + B_ij sin(δ_i − δ_j))
Q_i = |V_i| Σ_j |V_j| (G_ij sin(δ_i − δ_j) − B_ij cos(δ_i − δ_j))
```

Each iteration corrects the state vector by solving:

```
[ ΔP ]   [ H   N ] [ Δδ      ]
[ ΔQ ] = [ J'  L ] [ ΔV / V  ]
```

where H, N, J', L are the four Jacobian sub-matrices (partial derivatives of
P and Q with respect to δ and |V|).  The Jacobian is rebuilt each iteration
from the current voltage profile.

Convergence is quadratic once near the solution — practically four to six
iterations for well-conditioned transmission networks.  The solver declares
convergence when the L∞ norm of the mismatch vector falls below the specified
tolerance (default 10⁻⁶ pu).

See [docs/power_flow_theory.md](docs/power_flow_theory.md) for the complete
mathematical derivation, flat-start initialisation, bus type definitions, and
engineering tips for ill-conditioned systems.

### Y-Bus Formulation

The **nodal admittance matrix** Y-bus is the fundamental network model.  For
a branch with series admittance `y_s = 1/(R+jX)`, shunt susceptance `B`, and
off-nominal tap ratio `a = |a|∠φ`, the contributions are:

```
Y[i,i] += y_s / |a|²  +  jB/2
Y[j,j] += y_s          +  jB/2
Y[i,j] -= y_s / ā
Y[j,i] -= y_s / a
```

This handles transmission lines (`a = 1`, `φ = 0`) and phase-shifting
transformers uniformly in the same matrix structure.

### Fault Analysis

**Three-phase faults** are solved directly from the Thevenin impedance at the
faulted bus:

```
I_f = V_k^(0) / (Z_kk + Z_f)
```

**Single-line-to-ground (SLG) faults** require all three sequence networks
(positive, negative, zero) connected in series:

```
I_a^(1) = V_k^(0) / (Z_1,kk + Z_2,kk + Z_0,kk + 3·Z_f)
I_fault (phase A) = 3 × I_a^(1)
```

See [docs/fault_analysis_guide.md](docs/fault_analysis_guide.md) for
sequence network theory, zero-sequence network construction rules, example
calculations, and IEEE equipment rating guidance.

---

## Examples

### Power Flow — 3-Bus System

```python
from power_system import Bus, BusType, Line, build_ybus, NewtonRaphson

# Define buses (all quantities in pu on 100 MVA base)
slack = Bus("Bus-1", BusType.SLACK, v_pu=1.05)
gen   = Bus("Bus-2", BusType.PV,   v_pu=1.02, p_pu=1.0)
load  = Bus("Bus-3", BusType.PQ,   p_pu=-0.8, q_pu=-0.3)

buses = [slack, gen, load]

lines = [
    Line(slack, gen,  r_pu=0.01, x_pu=0.05, b_pu=0.02, rating_mva=200),
    Line(gen,   load, r_pu=0.02, x_pu=0.08, b_pu=0.03, rating_mva=150),
    Line(slack, load, r_pu=0.03, x_pu=0.09, b_pu=0.02, rating_mva=150),
]

Y = build_ybus(buses, lines)
result = NewtonRaphson().solve(buses, Y, tol=1e-6, max_iter=50)

if result.converged:
    print(f"Converged in {result.iterations} iterations")
    for bus in result.buses:
        print(bus)
```

### Loss Calculation

```python
from power_system import compute_losses

losses = compute_losses(buses, lines, base_mva=100.0)
print(f"Total losses: {losses['total_mw_loss']:.2f} MW  ({losses['loss_percent']:.2f}%)")

for branch in losses['line_losses']:
    print(f"  {branch['name']}: {branch['mw_loss']:.3f} MW")
```

### Fault Analysis — Three-Phase

```python
from power_system import FaultAnalysis

fa = FaultAnalysis(zf_pu=0.0)          # bolted fault

# Three-phase fault at bus index 2
result_3ph = fa.three_phase_fault(bus_idx=2, ybus=Y)
print(f"3Φ fault current: {result_3ph.i_fault_pu:.4f} pu")
print(f"Bus voltages during fault: {result_3ph.v_bus_pu}")
```

### Fault Analysis — Single-Line-to-Ground

```python
from power_system import FaultAnalysis
from power_system.ybus import ybus_to_zbus

fa = FaultAnalysis(zf_pu=0.0)

# Build sequence Z-bus matrices for your system
Z1 = ybus_to_zbus(Y_positive_sequence)
Z0 = ybus_to_zbus(Y_zero_sequence)

result_slg = fa.single_line_to_ground(bus_idx=2, z1=Z1, z0=Z0)
print(f"SLG fault current (phase A): {result_slg.i_fault_pu:.4f} pu")
```

### IEEE 9-Bus Test System

```bash
python examples/ieee_9bus.py
```

Expected output (abbreviated):

```
=================================================================
  IEEE 9-Bus Test System — Newton-Raphson Power Flow
  System base: 100.0 MVA,  230.0 kV
=================================================================

Solver status : CONVERGED
Iterations    : 4
Max mismatch  : 4.516e-09 pu

Bus Results
-----------------------------------------------------------------
Bus        Type   V (pu)   δ (deg)    P (MW)   Q (MVAR)
-----------------------------------------------------------------
Bus-1      Slack  1.0400     0.000     71.64      27.05
Bus-2      PV     1.0250     9.668    163.00      -0.65
Bus-3      PV     1.0250     4.771     85.00      -8.17
Bus-5      PQ     0.9957    -3.993   -125.00     -50.00
...

System Losses
  Total MW loss  : 4.986 MW
  Total MVAR loss: 15.612 MVAR
  Loss percentage: 1.57%
```

---

## API Reference

A full API reference with parameter types, return values, and examples for
every class and function is available in [docs/api_reference.md](docs/api_reference.md).

Quick summary:

| Symbol | Module | Description |
|---|---|---|
| `Bus` | `power_system.bus` | Network node dataclass |
| `BusType` | `power_system.bus` | Enum: SLACK / PV / PQ |
| `Line` | `power_system.line` | π-equivalent branch model |
| `build_ybus(buses, lines)` | `power_system.ybus` | Build Y-bus matrix |
| `ybus_to_zbus(ybus)` | `power_system.ybus` | Invert Y-bus → Z-bus |
| `NewtonRaphson().solve(buses, ybus)` | `power_system.power_flow` | Run power flow |
| `PowerFlowResult` | `power_system.power_flow` | Convergence info + bus results |
| `FaultAnalysis(zf_pu)` | `power_system.fault` | Fault calculator |
| `FaultResult` | `power_system.fault` | Fault currents + bus voltages |
| `compute_losses(buses, lines)` | `power_system.losses` | MW/MVAR loss breakdown |

---

## Engineering Background

This toolkit implements algorithms described in widely adopted IEEE standards
and textbooks:

- **IEEE Std 399-1997** (*Brown Book*) — Recommended Practice for Industrial
  and Commercial Power Systems Analysis.  Sections on load-flow and short-circuit
  analysis inform the formulation choices here.

- **IEEE 30-Bus and 9-Bus Test Systems** — Standardised benchmark networks
  maintained by the IEEE Power Systems Test Case Archive.  The bundled
  `ieee_9bus.py` replicates the WSCC 9-bus (Glover & Sarma, Ch. 6) and
  produces results consistent with published tables.

- **IEEE Std C37.010-2016** — Application Guide for AC High-Voltage Circuit
  Breakers.  The fault analysis module computes symmetrical fault currents as
  specified by this standard for breaker selection studies.

- **IEEE Std 141-1993** (*Red Book*) — Recommended Practice for Electric Power
  Distribution for Industrial Plants.  Short-circuit calculation methodology
  follows this reference.

- **Glover, Sarma & Overbye** — *Power System Analysis and Design*, 6th ed.
  The primary textbook reference for all algorithms (Y-bus formulation,
  Newton-Raphson Jacobian, Z-bus fault method, per-unit system).

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite covers:

- Y-bus construction (diagonal, off-diagonal, shunt B, tap ratio)
- Matrix symmetry and diagonal dominance checks
- Z-bus inversion round-trip accuracy
- Error handling (missing buses, zero reactance)

---

## Documentation

| Document | Description |
|---|---|
| [docs/getting_started.md](docs/getting_started.md) | Install, virtualenv setup, first run, result interpretation |
| [docs/power_flow_theory.md](docs/power_flow_theory.md) | Newton-Raphson math, Jacobian, bus types, convergence criteria |
| [docs/fault_analysis_guide.md](docs/fault_analysis_guide.md) | Symmetrical components, Z-bus fault method, SLG examples |
| [docs/api_reference.md](docs/api_reference.md) | Full API docs: every class, method, parameter, return type |

---

## License

MIT — see [LICENSE](LICENSE) for details.
