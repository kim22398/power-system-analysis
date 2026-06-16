# API Reference

Complete reference documentation for all public classes, functions, and data
containers in the `power_system` package.

---

## Module: `power_system.bus`

### `BusType`

```python
class BusType(str, Enum)
```

IEEE standard bus type classification.

| Member  | Value     | Description                             |
|---------|-----------|-----------------------------------------|
| `SLACK` | `"Slack"` | Reference bus; fixes angle to 0°        |
| `PV`    | `"PV"`    | Voltage-controlled generator bus        |
| `PQ`    | `"PQ"`    | Load bus; both P and Q are scheduled    |

---

### `Bus`

```python
@dataclass
class Bus
```

Represents a power system bus (network node).  All electrical quantities are
in per-unit on the system MVA base unless noted.

#### Constructor Parameters

| Parameter     | Type      | Default       | Description                                         |
|---------------|-----------|---------------|-----------------------------------------------------|
| `name`        | `str`     | required      | Human-readable identifier (e.g. `"Bus-1"`)          |
| `bus_type`    | `BusType` | `BusType.PQ`  | IEEE bus classification                             |
| `v_pu`        | `float`   | `1.0`         | Voltage magnitude in per-unit                       |
| `angle_rad`   | `float`   | `0.0`         | Voltage angle in radians                            |
| `p_pu`        | `float`   | `0.0`         | Net real power injection (gen − load), pu           |
| `q_pu`        | `float`   | `0.0`         | Net reactive power injection (gen − load), pu       |
| `p_load_pu`   | `float`   | `0.0`         | Real power load component, pu (informational)       |
| `q_load_pu`   | `float`   | `0.0`         | Reactive power load component, pu (informational)   |
| `p_gen_pu`    | `float`   | `0.0`         | Real power generation component, pu (informational) |
| `q_gen_pu`    | `float`   | `0.0`         | Reactive power generation, pu (informational)       |
| `q_min_pu`    | `float`   | `-9999.0`     | Minimum reactive generation limit (PV buses)        |
| `q_max_pu`    | `float`   | `9999.0`      | Maximum reactive generation limit (PV buses)        |
| `base_kv`     | `float`   | `1.0`         | Nominal voltage level in kV (reporting only)        |

**Raises:** `ValueError` if `name` is empty or `v_pu` ≤ 0.

#### Properties

| Property     | Type   | Description                              |
|--------------|--------|------------------------------------------|
| `is_slack`   | `bool` | `True` if `bus_type is BusType.SLACK`    |
| `is_pv`      | `bool` | `True` if `bus_type is BusType.PV`       |
| `is_pq`      | `bool` | `True` if `bus_type is BusType.PQ`       |

#### Methods

##### `voltage_complex() -> complex`

Return the complex phasor voltage V∠δ in rectangular form.

```python
V_complex = bus.voltage_complex()
# Returns: v_pu * exp(j * angle_rad)
```

**Returns:** `complex` — Complex voltage phasor in per-unit.

#### Example

```python
from power_system import Bus, BusType

slack = Bus("Substation-1", BusType.SLACK, v_pu=1.05, base_kv=230.0)
gen   = Bus("Gen-A",        BusType.PV,    v_pu=1.02, p_pu=2.0,
            q_min_pu=-0.5,  q_max_pu=1.0)
load  = Bus("Load-3",       BusType.PQ,    p_pu=-1.5, q_pu=-0.6)

print(slack.is_slack)            # True
print(gen.voltage_complex())     # (1.02+0j)
```

---

## Module: `power_system.line`

### `Line`

```python
@dataclass
class Line
```

Pi-equivalent model for a transmission line or transformer branch.

#### Constructor Parameters

| Parameter         | Type    | Default | Description                                        |
|-------------------|---------|---------|----------------------------------------------------|
| `from_bus`        | `Bus`   | required | Sending-end bus object                            |
| `to_bus`          | `Bus`   | required | Receiving-end bus object                          |
| `r_pu`            | `float` | required | Series resistance in per-unit                     |
| `x_pu`            | `float` | required | Series reactance in per-unit (must be non-zero)   |
| `b_pu`            | `float` | `0.0`   | Total shunt susceptance in per-unit (B_C)         |
| `rating_mva`      | `float` | `0.0`   | Thermal rating in MVA; 0 means unlimited          |
| `name`            | `str`   | `""`    | Branch label; auto-generated as `"from–to"` if blank |
| `tap_ratio`       | `float` | `1.0`   | Off-nominal transformer tap ratio                 |
| `phase_shift_rad` | `float` | `0.0`   | Phase-shift angle in radians                      |

**Raises:** `ValueError` if `x_pu == 0.0`.

#### Methods

##### `impedance_pu() -> complex`

Return the series impedance Z = R + jX in per-unit.

**Returns:** `complex`

---

##### `admittance() -> complex`

Return the series admittance y = 1 / Z in per-unit.

**Returns:** `complex`

---

##### `shunt_admittance() -> complex`

Return the total shunt admittance jB (purely susceptive for lossless shunt).

**Returns:** `complex`

---

##### `power_flow() -> tuple[complex, complex]`

Compute complex power injected into the branch at both terminals.

Uses bus voltage phasors stored in the connected `Bus` objects.  Must be
called after a converged power flow solution.

**Returns:** `tuple[complex, complex]`
  - `S_from` — Complex power (P + jQ, pu) at the sending end.
  - `S_to` — Complex power (P + jQ, pu) at the receiving end.
  - `S_from + S_to` equals total branch losses.

---

##### `loading_percent(base_mva: float = 100.0) -> float`

Return branch loading as a percentage of `rating_mva`.

| Parameter  | Type    | Default | Description              |
|------------|---------|---------|--------------------------|
| `base_mva` | `float` | `100.0` | System MVA base          |

**Returns:** `float` — Loading in percent, or `float('nan')` if no rating set.

#### Example

```python
from power_system import Bus, BusType, Line

b1 = Bus("B1", BusType.SLACK, v_pu=1.05)
b2 = Bus("B2", BusType.PQ,   v_pu=1.00)
line = Line(b1, b2, r_pu=0.01, x_pu=0.05, b_pu=0.02, rating_mva=200)

print(line.admittance())        # series admittance
print(line.impedance_pu())      # (0.01+0.05j)
```

---

## Module: `power_system.ybus`

### `build_ybus`

```python
def build_ybus(buses: Sequence[Bus], lines: Sequence[Line]) -> np.ndarray
```

Build the nodal admittance matrix (Y-bus) for a power network.

Implements the standard π-equivalent branch model with off-nominal tap ratio
and phase shift following Glover & Sarma formulation:

```
Y[i,i] += y_series / |a|²  +  jB/2
Y[j,j] += y_series          +  jB/2
Y[i,j] -= y_series / ā
Y[j,i] -= y_series / a
```

where `a = tap_ratio × exp(j × phase_shift_rad)`.

#### Parameters

| Parameter | Type             | Description                                              |
|-----------|------------------|----------------------------------------------------------|
| `buses`   | `Sequence[Bus]`  | Ordered bus list; index determines matrix row/column     |
| `lines`   | `Sequence[Line]` | All branches (transmission lines and transformers)       |

#### Returns

`numpy.ndarray` — Complex Y-bus matrix of shape `(n, n)`.

#### Raises

`ValueError` — If any line references a bus not present in `buses`.

#### Example

```python
from power_system import Bus, BusType, Line, build_ybus

b1 = Bus("B1", BusType.SLACK)
b2 = Bus("B2", BusType.PQ)
ln = Line(b1, b2, r_pu=0.02, x_pu=0.06)

Y = build_ybus([b1, b2], [ln])
print(Y.shape)   # (2, 2)
print(Y[0, 1])   # negative of series admittance
```

---

### `ybus_to_zbus`

```python
def ybus_to_zbus(ybus: np.ndarray) -> np.ndarray
```

Invert the Y-bus to obtain the Z-bus (impedance matrix).

The diagonal `Z[k,k]` is the Thevenin impedance at bus *k*, used directly
in fault current calculations.

#### Parameters

| Parameter | Type            | Description                    |
|-----------|-----------------|--------------------------------|
| `ybus`    | `numpy.ndarray` | Square complex admittance matrix |

#### Returns

`numpy.ndarray` — Z-bus matrix of shape `(n, n)`.

#### Raises

`numpy.linalg.LinAlgError` — If `ybus` is singular (network not grounded).

---

## Module: `power_system.power_flow`

### `PowerFlowResult`

```python
@dataclass
class PowerFlowResult
```

Container for Newton-Raphson power flow results.

#### Attributes

| Attribute        | Type        | Description                                          |
|------------------|-------------|------------------------------------------------------|
| `converged`      | `bool`      | `True` if solver reached specified tolerance         |
| `iterations`     | `int`       | Number of Newton iterations performed                |
| `mismatch_norm`  | `float`     | L∞ norm of final power mismatch vector (pu)          |
| `buses`          | `list[Bus]` | Bus list with updated `v_pu` and `angle_rad` values  |
| `p_slack_pu`     | `float`     | Real power injected at slack bus (pu)                |
| `q_slack_pu`     | `float`     | Reactive power injected at slack bus (pu)            |

---

### `NewtonRaphson`

```python
class NewtonRaphson
```

Full-Newton power flow solver using the polar form of the power equations.

Solves the nonlinear system iteratively:
```
[ ΔP ]   [ H   N ] [ Δδ      ]
[ ΔQ ] = [ J'  L ] [ ΔV / V  ]
```

#### Methods

##### `solve(buses, ybus, tol=1e-6, max_iter=50) -> PowerFlowResult`

Run the Newton-Raphson power flow.

Updates `v_pu` and `angle_rad` **in place** on each non-slack bus until
convergence or `max_iter` is reached.

| Parameter  | Type              | Default  | Description                                        |
|------------|-------------------|----------|----------------------------------------------------|
| `buses`    | `Sequence[Bus]`   | required | Ordered bus list; must contain exactly one slack   |
| `ybus`     | `numpy.ndarray`   | required | Nodal admittance matrix from `build_ybus`          |
| `tol`      | `float`           | `1e-6`   | Convergence tolerance on L∞ mismatch norm (pu)     |
| `max_iter` | `int`             | `50`     | Maximum Newton iterations                          |

**Returns:** `PowerFlowResult`

**Raises:** `ValueError` if bus list contains no slack bus or more than one.

#### Example

```python
from power_system import Bus, BusType, Line, build_ybus, NewtonRaphson

slack = Bus("S1", BusType.SLACK, v_pu=1.05)
load  = Bus("L1", BusType.PQ,   p_pu=-1.0, q_pu=-0.4)
line  = Line(slack, load, r_pu=0.01, x_pu=0.04)

Y = build_ybus([slack, load], [line])
result = NewtonRaphson().solve([slack, load], Y, tol=1e-8, max_iter=50)

print(f"Converged: {result.converged}, iterations: {result.iterations}")
print(f"Slack: P={result.p_slack_pu:.4f} pu, Q={result.q_slack_pu:.4f} pu")
```

---

## Module: `power_system.fault`

### `FaultResult`

```python
@dataclass
class FaultResult
```

Results container for a fault calculation.

#### Attributes

| Attribute          | Type            | Description                                         |
|--------------------|-----------------|-----------------------------------------------------|
| `fault_type`       | `str`           | Description, e.g. `"3-phase (balanced)"`            |
| `faulted_bus_idx`  | `int`           | Zero-based index of the faulted bus                 |
| `i_fault_pu`       | `float`         | Fault current magnitude in per-unit                 |
| `v_prefault_pu`    | `float`         | Pre-fault voltage at faulted bus (pu)               |
| `v_bus_pu`         | `numpy.ndarray` | Voltage magnitude at every bus during the fault (pu)|

---

### `FaultAnalysis`

```python
class FaultAnalysis
```

Fault analysis using the Z-bus method.  Supports balanced three-phase and
single-line-to-ground (SLG) faults.

#### Constructor

```python
FaultAnalysis(zf_pu: float = 0.0)
```

| Parameter | Type    | Default | Description                                    |
|-----------|---------|---------|------------------------------------------------|
| `zf_pu`   | `float` | `0.0`   | Fault impedance in pu (0 = bolted fault)       |

---

#### `three_phase_fault(bus_idx, ybus, v_prefault=None) -> FaultResult`

Compute a balanced three-phase fault at `bus_idx`.

| Parameter    | Type                           | Default | Description                                |
|--------------|--------------------------------|---------|--------------------------------------------|
| `bus_idx`    | `int`                          | required | Zero-based faulted bus index              |
| `ybus`       | `numpy.ndarray`                | required | Positive-sequence Y-bus matrix            |
| `v_prefault` | `float \| ndarray \| None`     | `None`  | Pre-fault voltages; defaults to 1∠0° pu   |

**Returns:** `FaultResult`

---

#### `single_line_to_ground(bus_idx, z1, z0, z2=None, v_prefault=None) -> FaultResult`

Compute a single-line-to-ground (SLG) fault at `bus_idx`.

Uses the method of symmetrical components; the phase-A fault current is
`I_a = 3 × I_a^(1)`.

| Parameter    | Type                       | Default  | Description                                           |
|--------------|----------------------------|----------|-------------------------------------------------------|
| `bus_idx`    | `int`                      | required | Zero-based faulted bus index                         |
| `z1`         | `numpy.ndarray`            | required | Positive-sequence Z-bus or Y-bus (auto-inverted)     |
| `z0`         | `numpy.ndarray`            | required | Zero-sequence Z-bus or Y-bus (auto-inverted)         |
| `z2`         | `numpy.ndarray \| None`    | `None`   | Negative-sequence Z-bus; defaults to `z1`            |
| `v_prefault` | `float \| ndarray \| None` | `None`   | Pre-fault voltages; defaults to 1∠0° pu              |

**Returns:** `FaultResult`

#### Example

```python
from power_system import Bus, BusType, Line, build_ybus, FaultAnalysis

buses = [Bus("B1", BusType.SLACK), Bus("B2", BusType.PQ)]
lines = [Line(buses[0], buses[1], r_pu=0.02, x_pu=0.06)]
Y = build_ybus(buses, lines)

fa = FaultAnalysis(zf_pu=0.0)   # bolted fault

# Three-phase fault at bus 1
r3ph = fa.three_phase_fault(bus_idx=1, ybus=Y)
print(f"3Φ fault current: {r3ph.i_fault_pu:.3f} pu")
print(f"Bus voltages: {r3ph.v_bus_pu}")
```

---

## Module: `power_system.losses`

### `compute_losses`

```python
def compute_losses(
    buses: Sequence[Bus],
    lines: Sequence[Line],
    base_mva: float = 100.0,
) -> dict[str, float]
```

Compute total transmission losses for a solved power system.

Must be called after the power flow has converged.  Branch losses are computed
from complex power flows at both terminals:
```
S_loss = S_from + S_to
```

#### Parameters

| Parameter  | Type             | Default | Description                               |
|------------|------------------|---------|-------------------------------------------|
| `buses`    | `Sequence[Bus]`  | required | Bus list with solved voltages and angles |
| `lines`    | `Sequence[Line]` | required | All branches in the network              |
| `base_mva` | `float`          | `100.0` | System MVA base for unit conversion      |

#### Returns

`dict[str, float | list]` with keys:

| Key              | Type            | Description                                  |
|------------------|-----------------|----------------------------------------------|
| `total_mw_loss`  | `float`         | Total real power losses (MW)                 |
| `total_mvar_loss`| `float`         | Total reactive power losses (MVAR)           |
| `loss_percent`   | `float`         | Losses as % of total generation              |
| `line_losses`    | `list[dict]`    | Per-branch list: `{name, mw_loss, mvar_loss}`|

#### Example

```python
from power_system import compute_losses

losses = compute_losses(buses, lines, base_mva=100.0)

print(f"Total: {losses['total_mw_loss']:.2f} MW, {losses['total_mvar_loss']:.2f} MVAR")
print(f"Loss %: {losses['loss_percent']:.2f}%")

for branch in losses['line_losses']:
    print(f"  {branch['name']}: {branch['mw_loss']:.3f} MW")
```

---

## Package-Level Imports

All public symbols are re-exported from the top-level `power_system` package:

```python
from power_system import (
    Bus,
    BusType,
    Line,
    build_ybus,
    NewtonRaphson,
    FaultAnalysis,
    compute_losses,
)
```

The sub-module symbols `PowerFlowResult`, `FaultResult`, and `ybus_to_zbus`
can be imported directly from their respective modules:

```python
from power_system.power_flow import PowerFlowResult
from power_system.fault import FaultResult
from power_system.ybus import ybus_to_zbus
```
