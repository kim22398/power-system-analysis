"""Formatted text reports for solved power-flow cases.

These helpers turn a solved network (bus voltages/angles already updated in
place by :class:`~power_system.power_flow.NewtonRaphson`) into readable,
fixed-width tables suitable for the console or a log file.
"""

from __future__ import annotations

import math
from typing import Sequence

from .bus import Bus
from .line import Line
from .losses import compute_losses
from .power_flow import PowerFlowResult


def bus_table(buses: Sequence[Bus], base_mva: float = 100.0) -> str:
    """Return a formatted bus-results table (V, angle, P, Q)."""
    width = 65
    lines = ["Bus Results", "-" * width]
    lines.append(
        f"{'Bus':<10} {'Type':<6} {'V (pu)':>8} {'delta(deg)':>11} "
        f"{'P (MW)':>9} {'Q (MVAR)':>10}"
    )
    lines.append("-" * width)
    for bus in buses:
        lines.append(
            f"{bus.name:<10} {bus.bus_type.value:<6} "
            f"{bus.v_pu:>8.4f} "
            f"{math.degrees(bus.angle_rad):>11.3f} "
            f"{bus.p_pu * base_mva:>9.2f} "
            f"{bus.q_pu * base_mva:>10.2f}"
        )
    lines.append("-" * width)
    return "\n".join(lines)


def line_table(lines_seq: Sequence[Line], base_mva: float = 100.0) -> str:
    """Return a formatted line-flow table (P/Q from, P to, loading %)."""
    width = 65
    out = ["Line Power Flows", "-" * width]
    out.append(
        f"{'Branch':<12} {'P_from(MW)':>12} {'Q_from(MVAR)':>14} "
        f"{'P_to(MW)':>11} {'Loading %':>10}"
    )
    out.append("-" * width)
    for line in lines_seq:
        s_from, s_to = line.power_flow()
        loading = line.loading_percent(base_mva)
        loading_str = f"{loading:>9.1f}%" if not math.isnan(loading) else "      N/A"
        out.append(
            f"{line.name:<12} "
            f"{s_from.real * base_mva:>12.2f} "
            f"{s_from.imag * base_mva:>14.2f} "
            f"{s_to.real * base_mva:>11.2f} "
            f"{loading_str}"
        )
    out.append("-" * width)
    return "\n".join(out)


def loss_summary(
    buses: Sequence[Bus],
    lines_seq: Sequence[Line],
    base_mva: float = 100.0,
) -> str:
    """Return a formatted system-loss summary block."""
    losses = compute_losses(buses, lines_seq, base_mva)
    return (
        "System Losses\n"
        f"  Total MW loss   : {losses['total_mw_loss']:.3f} MW\n"
        f"  Total MVAR loss : {losses['total_mvar_loss']:.3f} MVAR\n"
        f"  Loss percentage : {losses['loss_percent']:.2f}%"
    )


def full_report(
    result: PowerFlowResult,
    lines_seq: Sequence[Line],
    title: str = "Power Flow Report",
    base_mva: float = 100.0,
) -> str:
    """Assemble a complete report: header, convergence, buses, lines, losses."""
    width = 65
    status = "CONVERGED" if result.converged else "DID NOT CONVERGE"
    header = (
        "=" * width + "\n"
        f"  {title}\n"
        + "=" * width + "\n\n"
        f"Solver status : {status}\n"
        f"Iterations    : {result.iterations}\n"
        f"Max mismatch  : {result.mismatch_norm:.3e} pu\n"
    )
    return "\n".join(
        [
            header,
            bus_table(result.buses, base_mva),
            "",
            line_table(lines_seq, base_mva),
            "",
            loss_summary(result.buses, lines_seq, base_mva),
        ]
    )
