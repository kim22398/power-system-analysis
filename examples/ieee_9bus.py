"""IEEE 9-bus test system — power flow example.

This script builds the classic WSCC 9-bus system, runs Newton-Raphson power
flow, and prints a formatted results table.

Bus data (100 MVA base, 230 kV system):
    Bus 1 — Slack (generator)    V = 1.040 pu
    Bus 2 — PV   (generator)    V = 1.025 pu, P = 163 MW
    Bus 3 — PV   (generator)    V = 1.025 pu, P = 85  MW
    Buses 5, 6, 8 — load buses (PQ)
    Buses 4, 7, 9  — junction buses (PQ, no load)

Line data from Glover, Sarma & Overbye, "Power System Analysis and Design".
"""

import sys
import os

# Allow running directly from examples/ without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import numpy as np

from power_system.bus import Bus, BusType
from power_system.line import Line
from power_system.ybus import build_ybus
from power_system.power_flow import NewtonRaphson
from power_system.losses import compute_losses

BASE_MVA = 100.0
BASE_KV = 230.0


# ---------------------------------------------------------------------------
# Bus data
# ---------------------------------------------------------------------------

def build_buses() -> list[Bus]:
    buses = [
        Bus("Bus-1",  BusType.SLACK, v_pu=1.040, angle_rad=0.0,    p_pu=0.0,     q_pu=0.0,  base_kv=BASE_KV),
        Bus("Bus-2",  BusType.PV,   v_pu=1.025, angle_rad=0.0,    p_pu=1.63,    q_pu=0.0,  base_kv=BASE_KV),
        Bus("Bus-3",  BusType.PV,   v_pu=1.025, angle_rad=0.0,    p_pu=0.85,    q_pu=0.0,  base_kv=BASE_KV),
        Bus("Bus-4",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=0.0,     q_pu=0.0,  base_kv=BASE_KV),
        Bus("Bus-5",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=-1.25,   q_pu=-0.50, base_kv=BASE_KV),
        Bus("Bus-6",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=-0.90,   q_pu=-0.30, base_kv=BASE_KV),
        Bus("Bus-7",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=0.0,     q_pu=0.0,  base_kv=BASE_KV),
        Bus("Bus-8",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=-1.00,   q_pu=-0.35, base_kv=BASE_KV),
        Bus("Bus-9",  BusType.PQ,   v_pu=1.000, angle_rad=0.0,    p_pu=0.0,     q_pu=0.0,  base_kv=BASE_KV),
    ]
    return buses


# ---------------------------------------------------------------------------
# Branch data (lines + transformers represented as π equivalents, pu on 100 MVA)
# ---------------------------------------------------------------------------

def build_lines(buses: list[Bus]) -> list[Line]:
    b = {bus.name: bus for bus in buses}
    lines = [
        # Transformers (low X, no shunt B)
        Line(b["Bus-1"], b["Bus-4"], r_pu=0.0000, x_pu=0.0576, b_pu=0.000,  rating_mva=250, name="T1: 1-4"),
        Line(b["Bus-2"], b["Bus-7"], r_pu=0.0000, x_pu=0.0625, b_pu=0.000,  rating_mva=250, name="T2: 2-7"),
        Line(b["Bus-3"], b["Bus-9"], r_pu=0.0000, x_pu=0.0586, b_pu=0.000,  rating_mva=250, name="T3: 3-9"),
        # Transmission lines
        Line(b["Bus-4"], b["Bus-5"], r_pu=0.0100, x_pu=0.0850, b_pu=0.1760, rating_mva=250, name="L4-5"),
        Line(b["Bus-4"], b["Bus-6"], r_pu=0.0170, x_pu=0.0920, b_pu=0.1580, rating_mva=250, name="L4-6"),
        Line(b["Bus-5"], b["Bus-7"], r_pu=0.0320, x_pu=0.1610, b_pu=0.3060, rating_mva=250, name="L5-7"),
        Line(b["Bus-6"], b["Bus-9"], r_pu=0.0390, x_pu=0.1700, b_pu=0.3580, rating_mva=250, name="L6-9"),
        Line(b["Bus-7"], b["Bus-8"], r_pu=0.0085, x_pu=0.0720, b_pu=0.1490, rating_mva=250, name="L7-8"),
        Line(b["Bus-8"], b["Bus-9"], r_pu=0.0119, x_pu=0.1008, b_pu=0.2090, rating_mva=250, name="L8-9"),
    ]
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 65)
    print("  IEEE 9-Bus Test System — Newton-Raphson Power Flow")
    print(f"  System base: {BASE_MVA} MVA,  {BASE_KV} kV")
    print("=" * 65)

    buses = build_buses()
    lines = build_lines(buses)
    Y = build_ybus(buses, lines)

    solver = NewtonRaphson()
    result = solver.solve(buses, Y, tol=1e-6, max_iter=50)

    # ---- Print convergence summary ----
    status = "CONVERGED" if result.converged else "DID NOT CONVERGE"
    print(f"\nSolver status : {status}")
    print(f"Iterations    : {result.iterations}")
    print(f"Max mismatch  : {result.mismatch_norm:.3e} pu")

    # ---- Bus results table ----
    print("\nBus Results")
    print("-" * 65)
    print(f"{'Bus':<10} {'Type':<6} {'V (pu)':>8} {'δ (deg)':>9} {'P (MW)':>9} {'Q (MVAR)':>10}")
    print("-" * 65)
    for bus in result.buses:
        print(
            f"{bus.name:<10} {bus.bus_type.value:<6} "
            f"{bus.v_pu:>8.4f} "
            f"{math.degrees(bus.angle_rad):>9.3f} "
            f"{bus.p_pu * BASE_MVA:>9.2f} "
            f"{bus.q_pu * BASE_MVA:>10.2f}"
        )
    print("-" * 65)

    # ---- Line flow table ----
    print("\nLine Power Flows")
    print("-" * 65)
    print(f"{'Branch':<12} {'P_from (MW)':>12} {'Q_from (MVAR)':>14} {'P_to (MW)':>11} {'Loading %':>10}")
    print("-" * 65)
    for line in lines:
        s_from, s_to = line.power_flow()
        loading = line.loading_percent(BASE_MVA)
        loading_str = f"{loading:>9.1f}%" if not math.isnan(loading) else "      N/A"
        print(
            f"{line.name:<12} "
            f"{s_from.real * BASE_MVA:>12.2f} "
            f"{s_from.imag * BASE_MVA:>14.2f} "
            f"{s_to.real * BASE_MVA:>11.2f} "
            f"{loading_str}"
        )
    print("-" * 65)

    # ---- System losses ----
    losses = compute_losses(buses, lines, BASE_MVA)
    print(f"\nSystem Losses")
    print(f"  Total MW loss  : {losses['total_mw_loss']:.3f} MW")
    print(f"  Total MVAR loss: {losses['total_mvar_loss']:.3f} MVAR")
    print(f"  Loss percentage: {losses['loss_percent']:.2f}%")
    print()


if __name__ == "__main__":
    main()
