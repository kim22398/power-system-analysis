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

## Features

| Module | Description |
|---|---|
| `power_system/bus.py` | `Bus` dataclass — PQ / PV / Slack types, voltage phasors, limits |
| `power_system/line.py` | `Line` π-equivalent model with tap ratio and phase shift |
| `power_system/ybus.py` | Y-bus / Z-bus construction for arbitrary topologies |
| `power_system/power_flow.py` | Full Newton-Raphson solver (polar form, Jacobian submatrices) |
| `power_system/fault.py` | Three-phase and SLG fault analysis via symmetrical components |
| `power_system/losses.py` | Per-branch and system-total transmission loss computation |

---

## Installation

```bash
git clone https://github.com/your-username/power-system-analysis.git
cd power-system-analysis
pip install -r requirements.txt
```

No additional build step is required — the package is pure Python.

---

## Quick Start

### 1. Define buses and lines

```python
from power_system import Bus, BusType, Line, build_ybus, NewtonRaphson

# Define buses
slack = Bus("Bus-1", BusType.SLACK, v_pu=1.05)
gen   = Bus("Bus-2", BusType.PV,   v_pu=1.02,  p_pu=1.0)
load  = Bus("Bus-3", BusType.PQ,   p_pu=-0.8,  q_pu=-0.3)

buses = [slack, gen, load]

# Define transmission lines (per-unit on 100 MVA base)
lines = [
    Line(slack, gen,  r_pu=0.01, x_pu=0.05, b_pu=0.02, rating_mva=200),
    Line(gen,   load, r_pu=0.02, x_pu=0.08, b_pu=0.03, rating_mva=150),
    Line(slack, load, r_pu=0.03, x_pu=0.09, b_pu=0.02, rating_mva=150),
]
```

### 2. Build Y-bus and run power flow

```python
Y = build_ybus(buses, lines)

result = NewtonRaphson().solve(buses, Y, tol=1e-6, max_iter=50)

if result.converged:
    print(f"Converged in {result.iterations} iterations")
    for bus in result.buses:
        print(bus)
```

### 3. Compute losses

```python
from power_system import compute_losses

losses = compute_losses(buses, lines, base_mva=100.0)
print(f"Total losses: {losses['total_mw_loss']:.2f} MW  ({losses['loss_percent']:.2f}%)")
```

### 4. Fault analysis

```python
from power_system import FaultAnalysis

fa = FaultAnalysis(zf_pu=0.0)          # bolted fault

# Balanced three-phase fault at bus index 2
result_3ph = fa.three_phase_fault(bus_idx=2, ybus=Y)
print(f"3Φ fault current: {result_3ph.i_fault_pu:.4f} pu")

# Single-line-to-ground fault (requires separate sequence networks)
# result_slg = fa.single_line_to_ground(bus_idx=2, z1=Y1, z0=Y0)
```

---

## IEEE 9-Bus Example

The bundled example replicates the WSCC 9-bus test system from
*Glover, Sarma & Overbye, "Power System Analysis and Design"*, 6th ed.

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
```

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite covers:

- Y-bus construction (diagonal, off-diagonal, shunt B, tap ratio)
- Matrix symmetry and diagonal dominance
- Z-bus inversion round-trip
- Error handling (missing buses, zero reactance)

---

## Project Structure

```
power-system-analysis/
├── power_system/
│   ├── __init__.py
│   ├── bus.py          # Bus dataclass
│   ├── line.py         # Line π-model
│   ├── ybus.py         # Y-bus / Z-bus builder
│   ├── power_flow.py   # Newton-Raphson solver
│   ├── fault.py        # Fault analysis (3Φ and SLG)
│   └── losses.py       # Transmission loss computation
├── examples/
│   └── ieee_9bus.py    # IEEE 9-bus test system walkthrough
├── tests/
│   └── test_ybus.py    # Pytest unit tests
├── requirements.txt
└── README.md
```

---

## Technical Notes

### Power Flow Formulation

The Newton-Raphson solver uses the **polar form** of the power balance
equations with the classic Jacobian partition:

```
[ ΔP ]   [ H   N ] [ Δδ      ]
[ ΔQ ] = [ J'  L ] [ ΔV / V  ]
```

Slack bus angle is the reference (fixed at 0 rad). PV buses have fixed
voltage magnitude; only PQ buses update both voltage magnitude and angle.

### Y-Bus Model

The π-equivalent model for branches with off-nominal tap ratio *a* and
phase shift *φ* follows Glover & Sarma formulation:

```
Y[i,i] += y_series / |a|²  +  jB/2
Y[j,j] += y_series          +  jB/2
Y[i,j] -= y_series / ā
Y[j,i] -= y_series / a
```

This correctly handles both transmission lines (a=1, φ=0) and
phase-shifting transformers.

---

## License

MIT — see [LICENSE](LICENSE) for details.
