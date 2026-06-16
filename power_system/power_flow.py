"""Newton-Raphson power flow solver."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .bus import Bus, BusType


@dataclass
class PowerFlowResult:
    """Container for Newton-Raphson power flow results.

    Attributes
    ----------
    converged:
        ``True`` if the solver reached the specified tolerance.
    iterations:
        Number of iterations performed.
    mismatch_norm:
        L∞ norm of the final power mismatch vector (pu).
    buses:
        Reference to the bus list with updated voltage/angle values.
    p_slack_pu:
        Real power injected at the slack bus (pu).
    q_slack_pu:
        Reactive power injected at the slack bus (pu).
    """

    converged: bool
    iterations: int
    mismatch_norm: float
    buses: list[Bus]
    p_slack_pu: float = 0.0
    q_slack_pu: float = 0.0


class NewtonRaphson:
    """Full-Newton power flow solver using the polar form of the power equations.

    The solver iterates on the nonlinear system

    .. math::

        \\begin{bmatrix} \\Delta P \\\\ \\Delta Q \\end{bmatrix}
        = J \\begin{bmatrix} \\Delta\\delta \\\\ \\Delta V/V \\end{bmatrix}

    where *J* is the Jacobian partitioned into four sub-matrices
    (H, N, J, L in the classical notation).

    Example
    -------
    >>> from power_system import Bus, BusType, Line, build_ybus, NewtonRaphson
    >>> slack = Bus("Slack", BusType.SLACK, v_pu=1.05)
    >>> load  = Bus("Load",  BusType.PQ,    p_pu=-1.0, q_pu=-0.3)
    >>> line  = Line(slack, load, r_pu=0.02, x_pu=0.06)
    >>> Y     = build_ybus([slack, load], [line])
    >>> result = NewtonRaphson().solve([slack, load], Y)
    >>> result.converged
    True
    """

    def solve(
        self,
        buses: Sequence[Bus],
        ybus: np.ndarray,
        tol: float = 1e-6,
        max_iter: int = 50,
    ) -> PowerFlowResult:
        """Run the Newton-Raphson power flow.

        The method updates ``v_pu`` and ``angle_rad`` **in place** on each
        non-slack bus until convergence or ``max_iter`` is reached.

        Parameters
        ----------
        buses:
            Ordered list of :class:`~power_system.bus.Bus` objects.  Must
            contain exactly one slack bus.
        ybus:
            Nodal admittance matrix produced by
            :func:`~power_system.ybus.build_ybus`.
        tol:
            Convergence tolerance on the L∞ norm of the mismatch vector (pu).
        max_iter:
            Maximum number of Newton iterations.

        Returns
        -------
        PowerFlowResult
            Solution summary.  Bus objects are mutated in place.

        Raises
        ------
        ValueError
            If the bus list contains no slack bus or more than one.
        """
        buses = list(buses)
        n = len(buses)
        self._validate_slack(buses)

        slack_idx = next(i for i, b in enumerate(buses) if b.is_slack)

        # Identify PQ and PV buses (non-slack)
        pq_indices = [i for i, b in enumerate(buses) if b.is_pq]
        pv_indices = [i for i, b in enumerate(buses) if b.is_pv]
        non_slack = [i for i in range(n) if i != slack_idx]

        # State vector ordering:
        #   [ delta_i  (all non-slack) | V_i  (PQ buses only) ]
        iter_count = 0
        mismatch_norm = float("inf")

        for iter_count in range(1, max_iter + 1):
            # ---- Build voltage arrays ----
            V = np.array([b.v_pu for b in buses], dtype=float)
            delta = np.array([b.angle_rad for b in buses], dtype=float)

            # Complex voltages
            V_c = V * np.exp(1j * delta)

            # ---- Compute scheduled vs. calculated injections ----
            I_c = ybus @ V_c
            S_calc = V_c * np.conj(I_c)          # S = V * I*
            P_calc = S_calc.real
            Q_calc = S_calc.imag

            P_sch = np.array([b.p_pu for b in buses], dtype=float)
            Q_sch = np.array([b.q_pu for b in buses], dtype=float)

            dP = P_sch - P_calc   # mismatch for all buses
            dQ = Q_sch - Q_calc   # mismatch for PQ buses

            # ---- Build mismatch vector ----
            # dP for non-slack, dQ for PQ buses
            F = np.concatenate([
                dP[non_slack],
                dQ[pq_indices],
            ])

            mismatch_norm = np.max(np.abs(F))
            if mismatch_norm < tol:
                break

            # ---- Build Jacobian ----
            J = self._jacobian(buses, ybus, V, delta, non_slack, pq_indices, P_calc, Q_calc)

            # ---- Solve linear system ----
            try:
                dx = np.linalg.solve(J, F)
            except np.linalg.LinAlgError:
                break

            # ---- Update state variables ----
            n_non_slack = len(non_slack)
            d_delta = dx[:n_non_slack]
            d_V_over_V = dx[n_non_slack:]   # ΔV/V for PQ buses

            for k, i in enumerate(non_slack):
                buses[i].angle_rad += d_delta[k]

            for k, i in enumerate(pq_indices):
                buses[i].v_pu += d_V_over_V[k] * buses[i].v_pu

        # ---- Update slack bus injection ----
        V_c_final = np.array([b.v_pu * np.exp(1j * b.angle_rad) for b in buses])
        I_c_final = ybus @ V_c_final
        S_slack = V_c_final[slack_idx] * np.conj(I_c_final[slack_idx])
        buses[slack_idx].p_pu = S_slack.real
        buses[slack_idx].q_pu = S_slack.imag

        converged = mismatch_norm < tol
        return PowerFlowResult(
            converged=converged,
            iterations=iter_count,
            mismatch_norm=mismatch_norm,
            buses=buses,
            p_slack_pu=S_slack.real,
            q_slack_pu=S_slack.imag,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_slack(buses: list[Bus]) -> None:
        slack_buses = [b for b in buses if b.is_slack]
        if len(slack_buses) == 0:
            raise ValueError("Power flow requires exactly one slack bus; none found.")
        if len(slack_buses) > 1:
            raise ValueError(
                f"Power flow requires exactly one slack bus; found {len(slack_buses)}."
            )

    @staticmethod
    def _jacobian(
        buses: list[Bus],
        ybus: np.ndarray,
        V: np.ndarray,
        delta: np.ndarray,
        non_slack: list[int],
        pq_indices: list[int],
        P_calc: np.ndarray,
        Q_calc: np.ndarray,
    ) -> np.ndarray:
        """Construct the full Newton-Raphson Jacobian in polar form.

        The Jacobian is partitioned as::

            J = [ H   N ]
                [ J'  L ]

        where:
          * H[i,j] = dP_i/d(delta_j)
          * N[i,j] = dP_i/d(V_j) * V_j
          * J'[i,j] = dQ_i/d(delta_j)
          * L[i,j]  = dQ_i/d(V_j) * V_j
        """
        n = len(buses)
        G = ybus.real
        B = ybus.imag

        # Pre-compute full H, N, Jp, L matrices (n×n), then slice
        H = np.zeros((n, n))
        N = np.zeros((n, n))
        Jp = np.zeros((n, n))
        L = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    H[i, i] = -Q_calc[i] - B[i, i] * V[i] ** 2
                    N[i, i] =  P_calc[i] + G[i, i] * V[i] ** 2
                    Jp[i, i] = P_calc[i] - G[i, i] * V[i] ** 2
                    L[i, i] =  Q_calc[i] - B[i, i] * V[i] ** 2
                else:
                    theta_ij = delta[i] - delta[j]
                    Vi_Vj = V[i] * V[j]
                    H[i, j] = Vi_Vj * (
                        G[i, j] * math.sin(theta_ij) - B[i, j] * math.cos(theta_ij)
                    )
                    N[i, j] = Vi_Vj * (
                        G[i, j] * math.cos(theta_ij) + B[i, j] * math.sin(theta_ij)
                    )
                    Jp[i, j] = -Vi_Vj * (
                        G[i, j] * math.cos(theta_ij) + B[i, j] * math.sin(theta_ij)
                    )
                    L[i, j] = Vi_Vj * (
                        G[i, j] * math.sin(theta_ij) - B[i, j] * math.cos(theta_ij)
                    )

        # Slice to relevant rows/columns
        H_red = H[np.ix_(non_slack, non_slack)]
        N_red = N[np.ix_(non_slack, pq_indices)]
        Jp_red = Jp[np.ix_(pq_indices, non_slack)]
        L_red = L[np.ix_(pq_indices, pq_indices)]

        top = np.hstack([H_red, N_red])
        bot = np.hstack([Jp_red, L_red])
        return np.vstack([top, bot])
