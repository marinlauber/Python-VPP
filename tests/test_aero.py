"""Tests for AeroMod — wind triangle and coefficient caching."""

import numpy as np
import pytest


class TestWindTriangleCache:
    """Verify that wind_triangle uses lru_cache."""

    def test_wind_triangle_is_cached(self):
        from python_vpp.AeroMod import wind_triangle

        # lru_cache-decorated functions have cache_info()
        assert hasattr(wind_triangle, "cache_info"), "wind_triangle should be lru_cache-decorated"
        wind_triangle.cache_clear()
        wind_triangle(10.0, 90.0, 5.0)
        wind_triangle(10.0, 90.0, 5.0)
        info = wind_triangle.cache_info()
        assert info.hits == 1
        assert info.misses == 1

    def test_cache_returns_same_result(self):
        from python_vpp.AeroMod import wind_triangle

        wind_triangle.cache_clear()
        r1 = wind_triangle(10.0, 45.0, 6.0)
        r2 = wind_triangle(10.0, 45.0, 6.0)
        assert r1 == r2


class TestSailCoefficientCalls:
    """Verify that _get_coeffs doesn't call sail.cl() redundantly."""

    def test_get_coeffs_calls_cl_once_per_sail(self):
        """Each sail's cl(awa) should be called at most once per _get_coeffs()."""
        from unittest.mock import MagicMock, patch
        from python_vpp.AeroMod import AeroMod

        # Create a mock yacht with minimal structure
        mock_sail = MagicMock()
        mock_sail.cl = MagicMock(return_value=1.0)
        mock_sail.cd = MagicMock(return_value=0.1)
        mock_sail.area = 30.0
        mock_sail.bk = 1.0
        mock_sail.kp = 1.0
        mock_sail.type = "main"

        aero = object.__new__(AeroMod)
        aero.sails = [mock_sail]
        aero.area = 30.0
        aero.awa = 30.0
        aero.flat = 1.0
        aero.fcdmult = lambda flat: 1.0

        # Provide _heff so CE computation works
        aero._heff = lambda awa: 10.0

        aero._get_coeffs()

        # cl should be called exactly once per sail (not twice as before)
        assert mock_sail.cl.call_count == 1, (
            f"sail.cl() called {mock_sail.cl.call_count} times, expected 1"
        )
        assert mock_sail.cd.call_count == 1, (
            f"sail.cd() called {mock_sail.cd.call_count} times, expected 1"
        )


class TestWindTriangle:
    """Verify analytical wind triangle: given TWS, TWA, VB → AWS, AWA."""

    @pytest.mark.parametrize(
        "tws, twa, vb, expected_aws, expected_awa",
        [
            # Beam reach: TWA=90°, VB=5, TWS=10
            # AWS = sqrt(10² + 5² + 2·10·5·cos(90°)) = sqrt(125) ≈ 11.18
            # AWA = arccos((10·cos(90°) + 5) / 11.18) = arccos(5/11.18) ≈ 63.43°
            (10.0, 90.0, 5.0, np.sqrt(125), np.degrees(np.arccos(5.0 / np.sqrt(125)))),
            # Close-hauled: TWA=45°, VB=6, TWS=12
            (
                12.0,
                45.0,
                6.0,
                np.sqrt(12**2 + 6**2 + 2 * 12 * 6 * np.cos(np.radians(45))),
                np.degrees(
                    np.arccos(
                        (12 * np.cos(np.radians(45)) + 6)
                        / np.sqrt(12**2 + 6**2 + 2 * 12 * 6 * np.cos(np.radians(45)))
                    )
                ),
            ),
            # Dead downwind: TWA=180°, VB=4, TWS=10
            # AWS = sqrt(100 + 16 - 80) = sqrt(36) = 6
            # AWA = arccos((10·cos(180°) + 4) / 6) = arccos(-6/6) = 180°
            (10.0, 180.0, 4.0, 6.0, 180.0),
            # No boat speed: VB=0 → AWA=TWA, AWS=TWS
            (10.0, 90.0, 0.0, 10.0, 90.0),
            # Boat speed equals TWS, broad reach
            (8.0, 120.0, 8.0,
             np.sqrt(8**2 + 8**2 + 2 * 8 * 8 * np.cos(np.radians(120))),
             np.degrees(
                 np.arccos(
                     (8 * np.cos(np.radians(120)) + 8)
                     / np.sqrt(8**2 + 8**2 + 2 * 8 * 8 * np.cos(np.radians(120)))
                 )
             )),
        ],
        ids=["beam_reach", "close_hauled", "dead_downwind", "no_boat_speed", "broad_reach"],
    )
    def test_wind_triangle_analytical(self, tws, twa, vb, expected_aws, expected_awa):
        """AWA and AWS must match law-of-cosines closed-form solution."""
        from python_vpp.AeroMod import wind_triangle

        awa, aws = wind_triangle(tws, twa, vb)
        assert aws == pytest.approx(expected_aws, abs=1e-10)
        assert awa == pytest.approx(expected_awa, abs=1e-10)

    def test_no_fsolve_import_used(self):
        """The analytical path must not import or call fsolve."""
        from python_vpp.AeroMod import wind_triangle
        import inspect

        source = inspect.getsource(wind_triangle)
        assert "fsolve" not in source


class TestHeeledWindTriangle:
    """ORC 7.1: heel and the log wind gradient in the wind triangle."""

    def test_gradient_reference_height(self):
        from python_vpp.AeroMod import Z_REF, wind_gradient

        assert wind_gradient(Z_REF) == pytest.approx(1.0)
        assert wind_gradient(5.0) < 1.0 < wind_gradient(20.0)
        # ORC log profile, z0 = 0.005 m
        assert wind_gradient(5.0) == pytest.approx(np.log(1000.0) / np.log(2000.0))

    def test_heel_reduces_cross_wind(self):
        from python_vpp.AeroMod import wind_triangle

        awa0, aws0 = wind_triangle(10.0, 45.0, 3.0)
        awa, aws = wind_triangle(10.0, 45.0, 3.0, 30.0)
        vy = 10.0 * np.sin(np.radians(45.0)) * np.cos(np.radians(30.0))
        vx = 10.0 * np.cos(np.radians(45.0)) + 3.0
        assert aws == pytest.approx(np.hypot(vx, vy))
        assert awa == pytest.approx(np.degrees(np.arctan2(vy, vx)))
        assert awa < awa0 and aws < aws0
        # dead downwind heel has no effect
        heeled = wind_triangle(10.0, 180.0, 3.0, 20.0)
        assert heeled == pytest.approx(wind_triangle(10.0, 180.0, 3.0))
