"""Transmission line / branch model."""

from __future__ import annotations

from dataclasses import dataclass

from .bus import Bus


@dataclass
class Line:
    """Pi-equivalent model for a transmission line or transformer branch.

    All electrical parameters (R, X, B) are in per-unit on the system base.
    The model follows the standard π-circuit:

    ::

        from_bus ──[ R+jX ]──┬── to_bus
                             │
                           jB/2  (at each end)
                             │
                            GND

    Parameters
    ----------
    from_bus:
        Sending-end bus object.
    to_bus:
        Receiving-end bus object.
    r_pu:
        Series resistance in per-unit.
    x_pu:
        Series reactance in per-unit. Must not be zero.
    b_pu:
        Total shunt susceptance in per-unit (B = B_C for a capacitive line).
        The π model places B/2 at each terminal.
    rating_mva:
        Thermal rating in MVA (0 = unlimited). Used for overload checking.
    name:
        Optional descriptive label. Auto-generated from bus names if omitted.
    tap_ratio:
        Off-nominal transformer tap ratio (default 1.0 for lines).
    phase_shift_rad:
        Phase-shift angle in radians (default 0.0 for lines).
    """

    from_bus: Bus
    to_bus: Bus
    r_pu: float
    x_pu: float
    b_pu: float = 0.0
    rating_mva: float = 0.0
    name: str = ""
    tap_ratio: float = 1.0
    phase_shift_rad: float = 0.0

    def __post_init__(self) -> None:
        if self.x_pu == 0.0:
            raise ValueError(
                f"Line '{self.name or self._auto_name()}': series reactance X must not be zero."
            )
        if not self.name:
            self.name = self._auto_name()

    def _auto_name(self) -> str:
        return f"{self.from_bus.name}–{self.to_bus.name}"

    # ------------------------------------------------------------------
    # Electrical properties
    # ------------------------------------------------------------------

    def impedance_pu(self) -> complex:
        """Return the series impedance Z = R + jX in per-unit.

        Returns
        -------
        complex
            Series impedance phasor.
        """
        return complex(self.r_pu, self.x_pu)

    def admittance(self) -> complex:
        """Return the series admittance y = 1 / Z in per-unit.

        Returns
        -------
        complex
            Series admittance phasor.
        """
        return 1.0 / self.impedance_pu()

    def shunt_admittance(self) -> complex:
        """Return the total shunt admittance (purely susceptive for lossless shunt).

        Returns
        -------
        complex
            Total shunt admittance ``jB`` (split as B/2 at each end in the π model).
        """
        return complex(0.0, self.b_pu)

    def power_flow(self) -> tuple[complex, complex]:
        """Compute complex power flow from the sending end and receiving end.

        Uses the bus voltage phasors stored in the connected bus objects.

        Returns
        -------
        tuple[complex, complex]
            ``(S_from, S_to)`` — complex power (P + jQ) in per-unit injected
            into the line at the *from* end and at the *to* end respectively.
            The difference ``S_from + S_to`` equals the total line losses.
        """
        v_f = self.from_bus.voltage_complex()
        v_t = self.to_bus.voltage_complex()
        y_series = self.admittance()
        y_shunt = self.shunt_admittance()

        # Account for off-nominal tap
        a = self.tap_ratio * (1.0 + 0j)

        # Current injected into line from 'from' end
        i_from = (v_f / a - v_t) * y_series + (v_f / a) * (y_shunt / 2.0)
        s_from = v_f * i_from.conjugate()

        # Current injected into line from 'to' end
        i_to = (v_t - v_f / a) * y_series + v_t * (y_shunt / 2.0)
        s_to = v_t * i_to.conjugate()

        return s_from, s_to

    def loading_percent(self, base_mva: float = 100.0) -> float:
        """Return the line loading as a percentage of ``rating_mva``.

        Parameters
        ----------
        base_mva:
            System MVA base for converting pu flow to MVA.

        Returns
        -------
        float
            Loading in percent. Returns ``float('nan')`` when no rating is set.
        """
        if self.rating_mva <= 0:
            return float("nan")
        s_from, _ = self.power_flow()
        return abs(s_from) * base_mva / self.rating_mva * 100.0

    def __repr__(self) -> str:
        return (
            f"Line(name={self.name!r}, "
            f"Z={self.r_pu:.5f}+j{self.x_pu:.5f} pu, "
            f"B={self.b_pu:.5f} pu, rating={self.rating_mva} MVA)"
        )
