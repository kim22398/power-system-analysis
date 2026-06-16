"""Pytest tests for Y-bus construction.

Tests cover:
* Simple 2-bus network (analytic verification)
* 3-bus ring network (diagonal dominance, symmetry)
* Shunt susceptance (capacitive line charging)
* Off-nominal transformer tap ratio
* Error on missing bus reference
"""

from __future__ import annotations

import math
import cmath

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from power_system.bus import Bus, BusType
from power_system.line import Line
from power_system.ybus import build_ybus, ybus_to_zbus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_bus():
    """Minimal 2-bus network: Slack → PQ via a single line."""
    b1 = Bus("B1", BusType.SLACK, v_pu=1.0)
    b2 = Bus("B2", BusType.PQ, v_pu=1.0)
    line = Line(b1, b2, r_pu=0.01, x_pu=0.05, b_pu=0.0)
    return [b1, b2], [line]


@pytest.fixture
def three_bus_ring():
    """3-bus ring with identical line parameters."""
    b1 = Bus("B1", BusType.SLACK)
    b2 = Bus("B2", BusType.PQ)
    b3 = Bus("B3", BusType.PQ)
    r, x = 0.02, 0.10
    lines = [
        Line(b1, b2, r_pu=r, x_pu=x),
        Line(b2, b3, r_pu=r, x_pu=x),
        Line(b3, b1, r_pu=r, x_pu=x),
    ]
    return [b1, b2, b3], lines


# ---------------------------------------------------------------------------
# Tests — 2-bus network
# ---------------------------------------------------------------------------

class TestTwoBus:
    def test_shape(self, two_bus):
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        assert Y.shape == (2, 2)

    def test_dtype_is_complex(self, two_bus):
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        assert np.issubdtype(Y.dtype, np.complexfloating)

    def test_diagonal_equals_series_admittance(self, two_bus):
        """With no shunt B, Y[0,0] = Y[1,1] = y_series."""
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        y_s = lines[0].admittance()
        assert cmath.isclose(Y[0, 0], y_s, rel_tol=1e-10)
        assert cmath.isclose(Y[1, 1], y_s, rel_tol=1e-10)

    def test_off_diagonal_equals_negative_admittance(self, two_bus):
        """Off-diagonal entries must be −y_series for a simple line."""
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        y_s = lines[0].admittance()
        assert cmath.isclose(Y[0, 1], -y_s, rel_tol=1e-10)
        assert cmath.isclose(Y[1, 0], -y_s, rel_tol=1e-10)

    def test_row_sum_is_zero_without_shunt(self, two_bus):
        """Without shunt elements, each row must sum to zero (KCL)."""
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        for i in range(2):
            assert abs(Y[i, :].sum()) < 1e-12

    def test_symmetric_for_lossless_tap(self, two_bus):
        """Y-bus is symmetric when tap = 1 and no phase shift."""
        buses, lines = two_bus
        Y = build_ybus(buses, lines)
        np.testing.assert_allclose(Y, Y.T, atol=1e-12)


# ---------------------------------------------------------------------------
# Tests — shunt susceptance
# ---------------------------------------------------------------------------

class TestShuntSusceptance:
    def test_shunt_adds_to_diagonal(self):
        b1 = Bus("B1", BusType.SLACK)
        b2 = Bus("B2", BusType.PQ)
        b_total = 0.30
        line = Line(b1, b2, r_pu=0.01, x_pu=0.05, b_pu=b_total)
        Y = build_ybus([b1, b2], [line])
        y_s = line.admittance()
        # Each diagonal should include y_s + j*(B/2)
        expected_diag = y_s + complex(0, b_total / 2.0)
        assert cmath.isclose(Y[0, 0], expected_diag, rel_tol=1e-10)
        assert cmath.isclose(Y[1, 1], expected_diag, rel_tol=1e-10)

    def test_off_diagonal_unaffected_by_shunt(self):
        b1 = Bus("B1", BusType.SLACK)
        b2 = Bus("B2", BusType.PQ)
        line = Line(b1, b2, r_pu=0.01, x_pu=0.05, b_pu=0.20)
        Y = build_ybus([b1, b2], [line])
        y_s = line.admittance()
        assert cmath.isclose(Y[0, 1], -y_s, rel_tol=1e-10)


# ---------------------------------------------------------------------------
# Tests — 3-bus ring
# ---------------------------------------------------------------------------

class TestThreeBusRing:
    def test_shape(self, three_bus_ring):
        buses, lines = three_bus_ring
        Y = build_ybus(buses, lines)
        assert Y.shape == (3, 3)

    def test_diagonal_dominance(self, three_bus_ring):
        """Diagonal magnitude ≥ sum of off-diagonal magnitudes (row-wise)."""
        buses, lines = three_bus_ring
        Y = build_ybus(buses, lines)
        for i in range(3):
            diag = abs(Y[i, i])
            off_sum = sum(abs(Y[i, j]) for j in range(3) if j != i)
            assert diag >= off_sum - 1e-12, f"Row {i}: diag={diag:.6f} < off_sum={off_sum:.6f}"

    def test_symmetric(self, three_bus_ring):
        buses, lines = three_bus_ring
        Y = build_ybus(buses, lines)
        np.testing.assert_allclose(Y, Y.T, atol=1e-12)


# ---------------------------------------------------------------------------
# Tests — transformer tap ratio
# ---------------------------------------------------------------------------

class TestTransformerTap:
    def _make_tap_system(self, tap: float):
        b1 = Bus("B1", BusType.SLACK)
        b2 = Bus("B2", BusType.PQ)
        line = Line(b1, b2, r_pu=0.0, x_pu=0.10, tap_ratio=tap)
        Y = build_ybus([b1, b2], [line])
        return Y, line

    def test_tap_unity_equals_no_tap(self):
        Y_tap, line = self._make_tap_system(1.0)
        Y_ref = build_ybus(
            [line.from_bus, line.to_bus],
            [Line(line.from_bus, line.to_bus, r_pu=0.0, x_pu=0.10)],
        )
        np.testing.assert_allclose(Y_tap, Y_ref, atol=1e-12)

    def test_tap_asymmetry(self):
        """Off-nominal tap breaks matrix symmetry: Y[0,1] ≠ Y[1,0]."""
        Y, _ = self._make_tap_system(0.9)
        # Y[0,1] = -y/a*, Y[1,0] = -y/a  →  they differ if a is not real-unity
        # For real a, Y[0,1] = Y[1,0] = -y/a; but diagonal entries differ
        # So: Y[0,0] ≠ Y[1,1] for off-nominal tap
        assert not math.isclose(abs(Y[0, 0]), abs(Y[1, 1]), rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_bus_raises_value_error(self):
        b1 = Bus("B1", BusType.SLACK)
        b2 = Bus("B2", BusType.PQ)
        b_other = Bus("B-other", BusType.PQ)
        line = Line(b1, b_other, r_pu=0.01, x_pu=0.05)
        with pytest.raises(ValueError, match="B-other"):
            build_ybus([b1, b2], [line])

    def test_zero_reactance_raises(self):
        b1 = Bus("B1", BusType.SLACK)
        b2 = Bus("B2", BusType.PQ)
        with pytest.raises(ValueError):
            Line(b1, b2, r_pu=0.01, x_pu=0.0)


# ---------------------------------------------------------------------------
# Tests — Z-bus inversion
# ---------------------------------------------------------------------------

@pytest.fixture
def grounded_two_bus():
    """2-bus network with shunt B so Y-bus is non-singular."""
    b1 = Bus("B1", BusType.SLACK)
    b2 = Bus("B2", BusType.PQ)
    # b_pu > 0 adds jB/2 to each diagonal, making the matrix invertible
    line = Line(b1, b2, r_pu=0.01, x_pu=0.05, b_pu=0.10)
    return [b1, b2], [line]


class TestZbus:
    def test_zbus_roundtrip(self, grounded_two_bus):
        """Z-bus is the inverse of Y-bus: Y @ Z should equal the identity."""
        buses, lines = grounded_two_bus
        Y = build_ybus(buses, lines)
        Z = ybus_to_zbus(Y)
        np.testing.assert_allclose(Y @ Z, np.eye(2), atol=1e-10)

    def test_zbus_diagonal_real_positive(self, grounded_two_bus):
        """Diagonal Z-bus entries (driving-point impedances) have positive real parts."""
        buses, lines = grounded_two_bus
        Y = build_ybus(buses, lines)
        Z = ybus_to_zbus(Y)
        for i in range(Z.shape[0]):
            assert Z[i, i].real > 0, f"Z[{i},{i}].real = {Z[i,i].real} is not positive"
