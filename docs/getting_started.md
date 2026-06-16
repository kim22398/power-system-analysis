# Getting Started

This tutorial walks through everything you need to run a power flow study with
the Power System Analysis Toolkit — from a fresh Python installation through to
interpreting the IEEE 9-bus results.

---

## Prerequisites

- **Python 3.9 or later** — [download from python.org](https://www.python.org/downloads/)
- **git** — for cloning the repository
- Basic familiarity with per-unit notation and AC power systems

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/power-system-analysis.git
cd power-system-analysis
```

---

## Step 2 — Create a Virtual Environment

Using a virtual environment keeps project dependencies isolated from your
system Python installation.

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your shell prompt should now show `(.venv)` to indicate the environment is
active.

---

## Step 3 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The `requirements.txt` installs:

| Package    | Purpose                          |
|------------|----------------------------------|
| numpy      | Array arithmetic, matrix algebra |
| scipy      | Sparse matrix support            |
| pandas     | Tabular results (optional)       |
| matplotlib | Plotting (optional)              |
| pytest     | Running unit tests               |

---

## Step 4 — Verify the Installation

Run the unit test suite to confirm everything is working:

```bash
pytest tests/ -v
```

Expected output:

```
========================= test session starts ==========================
platform ... -- Python 3.x.x
tests/test_ybus.py::test_ybus_2bus_diagonal         PASSED
tests/test_ybus.py::test_ybus_2bus_off_diagonal     PASSED
tests/test_ybus.py::test_ybus_symmetry              PASSED
tests/test_ybus.py::test_zbus_roundtrip             PASSED
========================== 4 passed in 0.12s ===========================
```

---

## Step 5 — Run the IEEE 9-Bus Example

The bundled example replicates the classic WSCC 9-bus test system from
Glover, Sarma & Overbye.

```bash
python examples/ieee_9bus.py
```

You should see output similar to:

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
Bus-4      PQ     1.0258     2.407      0.00       0.00
Bus-5      PQ     0.9957    -3.993   -125.00     -50.00
Bus-6      PQ     1.0127    -3.686    -90.00     -30.00
Bus-7      PQ     1.0258     3.720      0.00       0.00
Bus-8      PQ     1.0159     0.727   -100.00     -35.00
Bus-9      PQ     1.0324     1.967      0.00       0.00
-----------------------------------------------------------------

Line Power Flows
-----------------------------------------------------------------
Branch       P_from (MW)  Q_from (MVAR)   P_to (MW)  Loading %
-----------------------------------------------------------------
T1: 1-4           71.64          27.05      -71.64      28.7%
...

System Losses
  Total MW loss  : 4.986 MW
  Total MVAR loss: 15.612 MVAR
  Loss percentage: 1.57%
```

---

## Step 6 — Interpreting the Results

### Bus Results Table

| Column  | Meaning                                                        |
|---------|----------------------------------------------------------------|
| V (pu)  | Solved voltage magnitude in per-unit                           |
| δ (deg) | Voltage angle in degrees (Bus-1 slack is 0° by definition)     |
| P (MW)  | Net real power injection (positive = generation, negative = load) |
| Q (MVAR)| Net reactive power injection                                   |

Voltage magnitudes should remain within **±5% of 1.0 pu** (0.95–1.05 pu)
under normal operating conditions per NERC reliability standards.

### Convergence Indicators

- **CONVERGED** with **4 iterations** — typical for well-conditioned
  transmission networks with a flat start.
- **Max mismatch** of ~10⁻⁹ pu — well below the 10⁻⁶ pu tolerance,
  confirming a tight solution.

### System Losses

Total losses of ~5 MW on a 319.6 MW generation dispatch equals ~1.6% — a
realistic figure for a lightly loaded 230 kV network.

---

## Step 7 — Write Your First Custom Case

Create a new Python script and define a simple three-bus system:

```python
from power_system import Bus, BusType, Line, build_ybus, NewtonRaphson, compute_losses

# Define buses (per-unit on 100 MVA base)
slack = Bus("Bus-1", BusType.SLACK, v_pu=1.05)
gen   = Bus("Bus-2", BusType.PV,    v_pu=1.02, p_pu=1.0)
load  = Bus("Bus-3", BusType.PQ,    p_pu=-0.8, q_pu=-0.3)

buses = [slack, gen, load]

# Define branches
lines = [
    Line(slack, gen,  r_pu=0.01, x_pu=0.05, b_pu=0.02, rating_mva=200),
    Line(gen,   load, r_pu=0.02, x_pu=0.08, b_pu=0.03, rating_mva=150),
    Line(slack, load, r_pu=0.03, x_pu=0.09, b_pu=0.02, rating_mva=150),
]

# Build admittance matrix and solve
Y = build_ybus(buses, lines)
result = NewtonRaphson().solve(buses, Y, tol=1e-6, max_iter=50)

if result.converged:
    print(f"Converged in {result.iterations} iterations")
    for bus in result.buses:
        print(f"  {bus.name}: V={bus.v_pu:.4f} pu, δ={bus.angle_rad:.4f} rad")

# Compute losses
losses = compute_losses(buses, lines, base_mva=100.0)
print(f"Total losses: {losses['total_mw_loss']:.2f} MW")
```

---

## Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ValueError: no slack bus` | No bus with `BusType.SLACK` in list | Add exactly one slack bus |
| `ValueError: X must not be zero` | Transformer or line with `x_pu=0` | Set a small non-zero reactance (e.g. 1e-6) |
| Does not converge | Overloaded network or poor starting point | Reduce load, check reactive limits |
| `LinAlgError: singular matrix` | Islands in network | Ensure all buses are connected |

---

## Next Steps

- Read [Power Flow Theory](power_flow_theory.md) for the mathematical
  background on Newton-Raphson.
- Read [Fault Analysis Guide](fault_analysis_guide.md) for three-phase
  and SLG fault calculations.
- Consult the [API Reference](api_reference.md) for full parameter documentation.
