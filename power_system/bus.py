"""Bus model for power system network nodes."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class BusType(str, Enum):
    """IEEE bus type classification."""

    SLACK = "Slack"   # Voltage angle reference (type 1)
    PV = "PV"         # Voltage-controlled (type 2)
    PQ = "PQ"         # Load bus (type 3)


@dataclass
class Bus:
    """Represents a power system bus (node).

    Voltages and angles are in per-unit (pu) and radians respectively.
    Power injections (P, Q) are in per-unit on the system MVA base.

    Parameters
    ----------
    name:
        Human-readable bus identifier (e.g. ``"Bus-1"`` or ``"Gen-A"``).
    bus_type:
        IEEE bus classification. Defaults to ``BusType.PQ``.
    v_pu:
        Voltage magnitude in per-unit. Defaults to 1.0 pu.
    angle_rad:
        Voltage angle in radians. Defaults to 0.0 rad.
    p_pu:
        Net scheduled real power injection in per-unit (generation − load).
        Positive values indicate net generation.
    q_pu:
        Net scheduled reactive power injection in per-unit (generation − load).
        Positive values indicate net generation.
    p_load_pu:
        Real power load in per-unit (positive = consuming).
    q_load_pu:
        Reactive power load in per-unit (positive = consuming).
    p_gen_pu:
        Real power generation in per-unit.
    q_gen_pu:
        Reactive power generation in per-unit.
    q_min_pu:
        Minimum reactive power generation limit in per-unit (PV buses).
    q_max_pu:
        Maximum reactive power generation limit in per-unit (PV buses).
    base_kv:
        Nominal voltage level in kV (informational only; not used in pu calc).
    """

    name: str
    bus_type: BusType = BusType.PQ
    v_pu: float = 1.0
    angle_rad: float = 0.0

    # Scheduled net injections (p_pu = p_gen_pu - p_load_pu, etc.)
    p_pu: float = 0.0
    q_pu: float = 0.0

    # Detailed load / gen breakdown (optional; informational)
    p_load_pu: float = 0.0
    q_load_pu: float = 0.0
    p_gen_pu: float = 0.0
    q_gen_pu: float = 0.0

    # Reactive power limits for PV buses
    q_min_pu: float = -9999.0
    q_max_pu: float = 9999.0

    # Nominal voltage (kV) — used for results reporting
    base_kv: float = 1.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Bus name must not be empty.")
        if self.v_pu <= 0:
            raise ValueError(f"Bus '{self.name}': voltage magnitude must be positive.")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_slack(self) -> bool:
        """Return ``True`` if this is the slack (reference) bus."""
        return self.bus_type is BusType.SLACK

    @property
    def is_pv(self) -> bool:
        """Return ``True`` if this is a PV (voltage-controlled) bus."""
        return self.bus_type is BusType.PV

    @property
    def is_pq(self) -> bool:
        """Return ``True`` if this is a PQ (load) bus."""
        return self.bus_type is BusType.PQ

    def voltage_complex(self) -> complex:
        """Return the complex phasor voltage V∠δ in rectangular form."""
        import cmath
        return self.v_pu * cmath.exp(1j * self.angle_rad)

    def __repr__(self) -> str:
        return (
            f"Bus(name={self.name!r}, type={self.bus_type.value}, "
            f"V={self.v_pu:.4f} pu, δ={self.angle_rad:.4f} rad, "
            f"P={self.p_pu:.4f} pu, Q={self.q_pu:.4f} pu)"
        )
