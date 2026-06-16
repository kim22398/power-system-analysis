"""Y-bus (admittance matrix) construction for a power system network."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .bus import Bus
from .line import Line


def build_ybus(buses: Sequence[Bus], lines: Sequence[Line]) -> np.ndarray:
    """Build the nodal admittance matrix (Y-bus) for a power network.

    Implements the standard π-equivalent branch model including:

    * Series admittance  ``y_series = 1 / (R + jX)``
    * Shunt susceptance  ``B/2`` at each terminal
    * Off-nominal tap ratio and phase shift for transformer branches

    The matrix entries follow the conventional rules:

    * Diagonal ``Y[i,i]``: sum of all admittances connected to bus *i*
      (series + shunt).
    * Off-diagonal ``Y[i,j]``: negative of the series admittance between
      buses *i* and *j*.

    Parameters
    ----------
    buses:
        Ordered sequence of :class:`~power_system.bus.Bus` objects.
        The index position in this sequence determines the row/column in
        the resulting matrix.
    lines:
        Sequence of :class:`~power_system.line.Line` objects representing
        all branches (lines and/or transformers) in the network.

    Returns
    -------
    numpy.ndarray
        Complex-valued Y-bus matrix of shape ``(n, n)`` where *n* is the
        number of buses.

    Raises
    ------
    ValueError
        If a line references a bus not present in *buses*.

    Examples
    --------
    >>> from power_system import Bus, BusType, Line, build_ybus
    >>> b1 = Bus("B1", BusType.SLACK)
    >>> b2 = Bus("B2", BusType.PQ)
    >>> ln = Line(b1, b2, r_pu=0.01, x_pu=0.05)
    >>> Y = build_ybus([b1, b2], [ln])
    >>> Y.shape
    (2, 2)
    """
    n = len(buses)
    bus_index: dict[str, int] = {bus.name: idx for idx, bus in enumerate(buses)}

    Y = np.zeros((n, n), dtype=complex)

    for line in lines:
        # Resolve bus indices
        try:
            i = bus_index[line.from_bus.name]
            j = bus_index[line.to_bus.name]
        except KeyError as exc:
            raise ValueError(
                f"Line '{line.name}' references bus {exc} which is not in the bus list."
            ) from exc

        y_s = line.admittance()       # series admittance
        y_sh = line.shunt_admittance()  # total shunt admittance (jB)
        a = line.tap_ratio * np.exp(1j * line.phase_shift_rad)  # tap + phase

        # Standard π-model with off-nominal tap (Glover & Sarma formulation)
        #
        #   Y[i,i] += y_s / |a|^2 + y_sh/2
        #   Y[j,j] += y_s          + y_sh/2
        #   Y[i,j] -= y_s / a*
        #   Y[j,i] -= y_s / a

        Y[i, i] += y_s / (abs(a) ** 2) + y_sh / 2.0
        Y[j, j] += y_s + y_sh / 2.0
        Y[i, j] -= y_s / np.conj(a)
        Y[j, i] -= y_s / a

    return Y


def ybus_to_zbus(ybus: np.ndarray) -> np.ndarray:
    """Invert the Y-bus to obtain the Z-bus (impedance matrix).

    Parameters
    ----------
    ybus:
        Square complex admittance matrix of shape ``(n, n)``.

    Returns
    -------
    numpy.ndarray
        Z-bus matrix of shape ``(n, n)``.

    Raises
    ------
    numpy.linalg.LinAlgError
        If *ybus* is singular (e.g. network is not properly grounded).
    """
    return np.linalg.inv(ybus)
