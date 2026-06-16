"""Symmetrical and asymmetrical fault analysis using the Z-bus method."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .ybus import ybus_to_zbus


@dataclass
class FaultResult:
    """Results from a fault calculation.

    Attributes
    ----------
    fault_type:
        Description of the fault type (e.g. ``"3-phase"``).
    faulted_bus_idx:
        Zero-based index of the faulted bus.
    i_fault_pu:
        Fault current magnitude in per-unit.
    v_prefault_pu:
        Pre-fault voltage magnitude at the faulted bus (pu).
    v_bus_pu:
        Voltage magnitude at each bus during the fault (pu).
    """

    fault_type: str
    faulted_bus_idx: int
    i_fault_pu: float
    v_prefault_pu: float
    v_bus_pu: np.ndarray


class FaultAnalysis:
    """Fault analysis using the Z-bus (impedance matrix) method.

    Supports both three-phase (balanced) and single-line-to-ground (SLG)
    faults assuming pre-fault voltages of 1∠0° pu at all buses.

    Parameters
    ----------
    zf_pu:
        Fault impedance in per-unit (default 0 for a bolted fault).

    References
    ----------
    Glover, Sarma & Overbye, "Power System Analysis and Design", 6th ed.,
    Ch. 9–10.
    """

    def __init__(self, zf_pu: float = 0.0) -> None:
        """Initialise the fault analyser.

        Parameters
        ----------
        zf_pu:
            Fault impedance in per-unit.  Use ``0.0`` (default) for a
            bolted (zero-impedance) fault, or a positive value to model
            arc resistance or grounding impedance.
        """
        self.zf_pu = zf_pu

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def three_phase_fault(
        self,
        bus_idx: int,
        ybus: np.ndarray,
        v_prefault: float | np.ndarray | None = None,
    ) -> FaultResult:
        """Compute a balanced three-phase fault at *bus_idx*.

        Parameters
        ----------
        bus_idx:
            Zero-based index of the faulted bus.
        ybus:
            Positive-sequence Y-bus matrix (n×n complex).
        v_prefault:
            Pre-fault voltage vector (pu).  If a scalar is given it is
            broadcast to all buses.  Defaults to 1∠0° everywhere.

        Returns
        -------
        FaultResult
            Fault current and bus voltages during the fault.
        """
        n = ybus.shape[0]
        zbus = ybus_to_zbus(ybus)

        v_pre = self._prefault_voltages(v_prefault, n)
        k = bus_idx

        # Fault current: I_f = V_k^0 / (Z_kk + Z_f)
        z_kk = zbus[k, k]
        v_k0 = v_pre[k]
        i_fault = v_k0 / (z_kk + complex(self.zf_pu))

        # Bus voltages during fault: V_i = V_i^0 - Z_ik * I_f
        v_fault = v_pre - zbus[:, k] * i_fault

        return FaultResult(
            fault_type="3-phase (balanced)",
            faulted_bus_idx=k,
            i_fault_pu=abs(i_fault),
            v_prefault_pu=abs(v_k0),
            v_bus_pu=np.abs(v_fault),
        )

    def single_line_to_ground(
        self,
        bus_idx: int,
        z1: np.ndarray,
        z0: np.ndarray,
        z2: np.ndarray | None = None,
        v_prefault: float | np.ndarray | None = None,
    ) -> FaultResult:
        """Compute a single-line-to-ground (SLG) fault at *bus_idx*.

        Uses the method of symmetrical components.  The fault current on
        phase A is:

        .. math::

            I_a^{(1)} = \\frac{V_k^0}{Z_{1,kk} + Z_{2,kk} + Z_{0,kk} + 3Z_f}

        and the phase-A fault current is ``I_a = 3 * I_a^{(1)}``.

        Parameters
        ----------
        bus_idx:
            Zero-based index of the faulted bus.
        z1:
            Positive-sequence Z-bus matrix (n×n complex). If you pass the
            **Y-bus**, it will be automatically inverted.
        z0:
            Zero-sequence Z-bus matrix (n×n complex).
        z2:
            Negative-sequence Z-bus matrix (n×n complex).  Defaults to the
            positive-sequence Z-bus (valid for static machines / lines).
        v_prefault:
            Pre-fault voltage vector (pu).  Defaults to 1∠0° everywhere.

        Returns
        -------
        FaultResult
            Fault current (3I_a^{(1)}) and positive-sequence bus voltages
            during the fault.
        """
        n = z1.shape[0]

        # Auto-detect if Y-bus passed (large diagonal magnitudes → invert)
        if np.max(np.abs(np.diag(z1))) < 1.0:
            pass  # already Z-bus
        else:
            z1 = ybus_to_zbus(z1)

        if np.max(np.abs(np.diag(z0))) > 1.0:
            z0 = ybus_to_zbus(z0)

        z2_mat = z1 if z2 is None else z2
        if np.max(np.abs(np.diag(z2_mat))) > 1.0:
            z2_mat = ybus_to_zbus(z2_mat)

        v_pre = self._prefault_voltages(v_prefault, n)
        k = bus_idx

        z1_kk = z1[k, k]
        z2_kk = z2_mat[k, k]
        z0_kk = z0[k, k]
        v_k0 = v_pre[k]
        zf = complex(self.zf_pu)

        # Sequence fault current (positive sequence)
        i1 = v_k0 / (z1_kk + z2_kk + z0_kk + 3.0 * zf)
        i2 = i1
        i0 = i1

        # Phase-A fault current magnitude (SLG: Ia = 3*I1)
        i_fault_a = 3.0 * i1

        # Positive-sequence bus voltages during fault
        v1_fault = v_pre - z1[:, k] * i1

        return FaultResult(
            fault_type="Single-Line-to-Ground (SLG)",
            faulted_bus_idx=k,
            i_fault_pu=abs(i_fault_a),
            v_prefault_pu=abs(v_k0),
            v_bus_pu=np.abs(v1_fault),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prefault_voltages(v_prefault: float | np.ndarray | None, n: int) -> np.ndarray:
        """Return a complex pre-fault voltage array of length *n*."""
        if v_prefault is None:
            return np.ones(n, dtype=complex)
        v = np.asarray(v_prefault, dtype=complex)
        if v.ndim == 0:
            return np.full(n, complex(v), dtype=complex)
        if v.shape != (n,):
            raise ValueError(
                f"v_prefault shape {v.shape} does not match n={n}."
            )
        return v
