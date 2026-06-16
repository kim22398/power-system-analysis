"""Command-line entry point for the Power System Analysis Toolkit.

This module exposes the library's core studies directly from the shell so the
project can be run without writing any Python:

* ``python main.py``               — run the flagship IEEE 9-bus demo
* ``python main.py --help``        — list every available subcommand
* ``python main.py powerflow``     — Newton-Raphson power flow + report tables
* ``python main.py fault``         — three-phase or SLG fault study at a bus
* ``python main.py test``          — run the pytest suite

The IEEE 9-bus WSCC test system (Glover, Sarma & Overbye, Ch. 6) is used as the
default network for the domain subcommands so they work out of the box with no
input files.
"""

from __future__ import annotations

# Make ``power_system`` importable when run as ``python main.py`` from anywhere,
# without requiring PYTHONPATH to be set.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import subprocess

import numpy as np

from examples.ieee_9bus import BASE_KV, BASE_MVA, build_buses, build_lines, main as run_demo
from power_system.bus import Bus
from power_system.line import Line
from power_system.power_flow import NewtonRaphson, PowerFlowResult
from power_system.report import bus_table, line_table, loss_summary
from power_system.fault import FaultAnalysis, FaultResult
from power_system.ybus import build_ybus


# ---------------------------------------------------------------------------
# Network helpers (shared by the domain subcommands)
# ---------------------------------------------------------------------------

def _solved_9bus(tol: float = 1e-6, max_iter: int = 50) -> tuple[PowerFlowResult, list[Line]]:
    """Build and solve the IEEE 9-bus system, returning the result and branches.

    Parameters
    ----------
    tol:
        Convergence tolerance on the L-infinity mismatch norm (pu).
    max_iter:
        Maximum number of Newton-Raphson iterations.

    Returns
    -------
    tuple[PowerFlowResult, list[Line]]
        The solved power-flow result (bus voltages updated in place) and the
        list of branches, ready for line-flow and loss reporting.
    """
    buses = build_buses()
    lines = build_lines(buses)
    ybus = build_ybus(buses, lines)
    result = NewtonRaphson().solve(buses, ybus, tol=tol, max_iter=max_iter)
    return result, lines


def _zero_sequence_lines(lines: list[Line], x0_mult: float, r0_mult: float) -> list[Line]:
    """Return a zero-sequence copy of *lines* with scaled series impedance.

    Real zero-sequence networks differ from the positive-sequence network:
    line reactance is typically 2.5-3x larger and resistance somewhat larger.
    Shunt charging is retained so the zero-sequence Y-bus stays non-singular
    (it provides the ground-return path, consistent with the positive-sequence
    matrix used elsewhere in this toolkit).

    Parameters
    ----------
    lines:
        Positive-sequence branch list.
    x0_mult:
        Multiplier applied to each branch reactance (typical: 3.0).
    r0_mult:
        Multiplier applied to each branch resistance (typical: 1.0).

    Returns
    -------
    list[Line]
        New :class:`~power_system.line.Line` objects sharing the same buses.
    """
    return [
        Line(
            ln.from_bus,
            ln.to_bus,
            r_pu=ln.r_pu * r0_mult,
            x_pu=ln.x_pu * x0_mult,
            b_pu=ln.b_pu,
            rating_mva=ln.rating_mva,
            name=ln.name,
            tap_ratio=ln.tap_ratio,
            phase_shift_rad=ln.phase_shift_rad,
        )
        for ln in lines
    ]


def _resolve_bus_index(buses: list[Bus], bus_number: int) -> int:
    """Translate a 1-based bus number into a 0-based list index.

    Parameters
    ----------
    buses:
        Ordered bus list (index position defines the Y-bus row/column).
    bus_number:
        Human-facing 1-based bus number (1 .. len(buses)).

    Returns
    -------
    int
        Zero-based index into *buses*.

    Raises
    ------
    SystemExit
        If *bus_number* is outside the valid range.
    """
    if not 1 <= bus_number <= len(buses):
        raise SystemExit(
            f"error: --bus {bus_number} out of range (valid: 1..{len(buses)})"
        )
    return bus_number - 1


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_demo(args: argparse.Namespace) -> int:
    """Run the flagship IEEE 9-bus demonstration (default, no subcommand)."""
    run_demo()
    return 0


def cmd_powerflow(args: argparse.Namespace) -> int:
    """Run Newton-Raphson power flow on the IEEE 9-bus case and print tables."""
    result, lines = _solved_9bus(tol=args.tol, max_iter=args.max_iter)

    width = 65
    status = "CONVERGED" if result.converged else "DID NOT CONVERGE"
    print("=" * width)
    print("  IEEE 9-Bus Power Flow (Newton-Raphson)")
    print(f"  System base: {BASE_MVA} MVA,  {BASE_KV} kV")
    print("=" * width)
    print(f"\nSolver status : {status}")
    print(f"Iterations    : {result.iterations}")
    print(f"Max mismatch  : {result.mismatch_norm:.3e} pu\n")

    print(bus_table(result.buses, BASE_MVA))
    print()
    print(line_table(lines, BASE_MVA))
    print()
    print(loss_summary(result.buses, lines, BASE_MVA))
    print()

    return 0 if result.converged else 1


def cmd_fault(args: argparse.Namespace) -> int:
    """Run a fault study (3-phase or SLG) at the requested bus."""
    buses = build_buses()
    lines = build_lines(buses)
    y1 = build_ybus(buses, lines)

    idx = _resolve_bus_index(buses, args.bus)
    fa = FaultAnalysis(zf_pu=args.zf)

    if args.type == "3ph":
        result: FaultResult = fa.three_phase_fault(bus_idx=idx, ybus=y1)
        extra = ""
    else:  # slg
        y0_lines = _zero_sequence_lines(lines, x0_mult=args.x0_mult, r0_mult=args.r0_mult)
        y0 = build_ybus(buses, y0_lines)
        result = fa.single_line_to_ground(bus_idx=idx, y1=y1, y0=y0)
        extra = f"  (zero-seq X0 = {args.x0_mult:g} x X1, R0 = {args.r0_mult:g} x R1)"

    _print_fault_report(result, buses, args.zf, extra)
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run the pytest suite (``python -m pytest tests/ -q``)."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", *args.pytest_args]
    env = dict(os.environ, PYTHONPATH=repo_root)
    return subprocess.call(cmd, cwd=repo_root, env=env)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _print_fault_report(
    result: FaultResult,
    buses: list[Bus],
    zf_pu: float,
    extra: str = "",
) -> None:
    """Print a formatted fault-study report (current + per-bus voltage dip).

    Parameters
    ----------
    result:
        Fault calculation result from :class:`~power_system.fault.FaultAnalysis`.
    buses:
        Bus list (used for human-readable bus names).
    zf_pu:
        Fault impedance used in the study (pu), echoed in the header.
    extra:
        Optional extra header line (e.g. zero-sequence assumptions).
    """
    width = 65
    faulted = buses[result.faulted_bus_idx]
    i_amps = result.i_fault_pu * BASE_MVA * 1e3 / (np.sqrt(3.0) * BASE_KV)

    print("=" * width)
    print(f"  Fault Study — {result.fault_type}")
    print(f"  Faulted bus  : {faulted.name}  (Z_f = {zf_pu:g} pu)")
    if extra:
        print(f" {extra}")
    print("=" * width)
    print(f"\nPre-fault voltage : {result.v_prefault_pu:.4f} pu")
    print(f"Fault current     : {result.i_fault_pu:.4f} pu  ({i_amps:,.1f} A on {BASE_KV:g} kV base)")

    print("\nBus Voltages During Fault")
    print("-" * width)
    print(f"{'Bus':<10} {'V (pu)':>10} {'V dip (%)':>12}")
    print("-" * width)
    for bus, v in zip(buses, result.v_bus_pu):
        dip = (1.0 - v) * 100.0
        marker = "  <-- faulted" if bus is faulted else ""
        print(f"{bus.name:<10} {v:>10.4f} {dip:>11.1f}%{marker}")
    print("-" * width)
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Power System Analysis Toolkit — steady-state power flow, fault "
            "studies, and losses on the IEEE 9-bus test system."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with no subcommand to launch the flagship IEEE 9-bus demo.",
    )
    parser.set_defaults(func=cmd_demo)

    sub = parser.add_subparsers(title="subcommands", metavar="<command>")

    # demo (explicit alias for the default behaviour)
    p_demo = sub.add_parser(
        "demo",
        help="run the flagship IEEE 9-bus demonstration",
        description="Run the flagship IEEE 9-bus power-flow demonstration.",
    )
    p_demo.set_defaults(func=cmd_demo)

    # powerflow
    p_pf = sub.add_parser(
        "powerflow",
        help="run Newton-Raphson power flow and print bus/line/loss tables",
        description=(
            "Solve the IEEE 9-bus system with the Newton-Raphson method and "
            "print bus voltages, line flows, and system losses."
        ),
    )
    p_pf.add_argument(
        "--tol",
        type=float,
        default=1e-6,
        help="convergence tolerance on the mismatch norm in pu (default: 1e-6)",
    )
    p_pf.add_argument(
        "--max-iter",
        type=int,
        default=50,
        dest="max_iter",
        help="maximum Newton-Raphson iterations (default: 50)",
    )
    p_pf.set_defaults(func=cmd_powerflow)

    # fault
    p_fault = sub.add_parser(
        "fault",
        help="run a fault study (3-phase or single-line-to-ground) at a bus",
        description=(
            "Run a short-circuit study at a bus of the IEEE 9-bus system using "
            "the Z-bus method, and print the fault current and per-bus voltage "
            "dip."
        ),
    )
    p_fault.add_argument(
        "--bus",
        type=int,
        default=5,
        metavar="N",
        help="1-based faulted bus number, 1..9 (default: 5)",
    )
    p_fault.add_argument(
        "--type",
        choices=("3ph", "slg"),
        default="3ph",
        help="fault type: 3ph = three-phase, slg = single-line-to-ground "
        "(default: 3ph)",
    )
    p_fault.add_argument(
        "--zf",
        type=float,
        default=0.0,
        help="fault impedance in pu, 0 = bolted fault (default: 0.0)",
    )
    p_fault.add_argument(
        "--x0-mult",
        type=float,
        default=3.0,
        dest="x0_mult",
        help="zero-seq reactance multiplier vs positive seq, SLG only "
        "(default: 3.0)",
    )
    p_fault.add_argument(
        "--r0-mult",
        type=float,
        default=1.0,
        dest="r0_mult",
        help="zero-seq resistance multiplier vs positive seq, SLG only "
        "(default: 1.0)",
    )
    p_fault.set_defaults(func=cmd_fault)

    # test
    p_test = sub.add_parser(
        "test",
        help="run the pytest suite (python -m pytest tests/ -q)",
        description="Run the project's pytest suite.",
    )
    p_test.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="extra arguments forwarded to pytest (e.g. -k name -v)",
    )
    p_test.set_defaults(func=cmd_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the selected subcommand.

    Parameters
    ----------
    argv:
        Argument list (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Process exit code (0 on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
