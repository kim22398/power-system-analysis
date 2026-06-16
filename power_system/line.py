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

        # Off-nominal tap (with optional phase shift), matching build_ybus.
        import cmath
        a = self.tap_ratio * cmath.exp(1j * self.phase_shift_rad)

        # Branch terminal currents, consistent with the off-nominal-tap
        # Y-bus model in build_ybus:
        #   Y[f,f] = y_series/|a|^2 + y_shunt/2 ,  Y[f,t] = -y_series/conj(a)
        #   Y[t,t] = y_series        + y_shunt/2 ,  Y[t,f] = -y_series/a
        # so  I_from = Y[f,f]*V_f + Y[f,t]*V_t , etc.
        i_from = (y_series / (abs(a) ** 2) + y_shunt / 2.0) * v_f \
            - (y_series / a.conjugate()) * v_t
        s_from = v_f * i_from.conjugate()

        i_to = (y_series + y_shunt / 2.0) * v_t - (y_series / a) * v_f
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
