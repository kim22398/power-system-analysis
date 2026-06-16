"""Transmission loss calculations for a solved power system."""

from __future__ import annotations

from typing import Sequence

from .bus import Bus
from .line import Line


def compute_losses(
    buses: Sequence[Bus],
    lines: Sequence[Line],
    base_mva: float = 100.0,
) -> dict[str, float]:
    """Compute total transmission losses for a solved power system.

    This function should be called **after** the power flow has converged so
    that bus voltages and angles reflect the operating point.

    For each branch the complex power loss is computed as

    .. math::

        S_{loss} = S_{from} + S_{to}

    where :math:`S_{from}` and :math:`S_{to}` are the complex power flows
    into the branch from each terminal (both positive when power *enters* the
    branch). Their sum equals losses because power leaving one end and not
    arriving at the other is dissipated.

    Parameters
    ----------
    buses:
        List of :class:`~power_system.bus.Bus` objects with solved voltages.
    lines:
        List of :class:`~power_system.line.Line` objects representing all
        branches in the network.
    base_mva:
        System MVA base used to convert per-unit results to physical units.

    Returns
    -------
    dict[str, float]
        Dictionary with the following keys:

        * ``total_mw_loss``    — Total real power losses in MW.
        * ``total_mvar_loss``  — Total reactive power losses in MVAR.
        * ``loss_percent``     — Losses as a percentage of total generation.
        * ``line_losses``      — List of per-branch dicts (name, mw, mvar).
    """
    total_p_loss_pu = 0.0
    total_q_loss_pu = 0.0
    line_losses: list[dict] = []

    for line in lines:
        s_from, s_to = line.power_flow()
        dp = (s_from + s_to).real   # real power loss (pu)
        dq = (s_from + s_to).imag   # reactive power loss (pu)
        total_p_loss_pu += dp
        total_q_loss_pu += dq
        line_losses.append(
            {
                "name": line.name,
                "mw_loss": dp * base_mva,
                "mvar_loss": dq * base_mva,
            }
        )

    # Total generation = sum of positive net injections (pu)
    total_gen_pu = sum(b.p_pu for b in buses if b.p_pu > 0)
    loss_pct = (
        100.0 * total_p_loss_pu / total_gen_pu if total_gen_pu > 0 else float("nan")
    )

    return {
        "total_mw_loss": total_p_loss_pu * base_mva,
        "total_mvar_loss": total_q_loss_pu * base_mva,
        "loss_percent": loss_pct,
        "line_losses": line_losses,
    }
