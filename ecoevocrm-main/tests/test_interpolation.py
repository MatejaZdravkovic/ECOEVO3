#!/usr/bin/env python
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Interpolation Utility Test Suite
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Comprehensive tests for align_xy_for_interp and related functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from ecoevocrm.gui.interpolation_utils import (
    align_xy_for_interp,
    validate_interpolation_inputs,
    safe_interp1d,
    safe_np_interp
)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Test Suite
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_length_mismatch():
    """Test that length mismatch is handled by truncating to min length."""
    print("\n=== TEST: Length Mismatch ===")
    x = np.array([0, 1, 2, 3, 4])
    y = np.array([10, 20, 30])  # Shorter

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should be valid after truncation"
    assert len(x_clean) == len(y_clean) == 3, f"Should truncate to 3, got x={len(x_clean)}, y={len(y_clean)}"
    assert 'truncated' in status['actions'], "Should report truncation"

    print("[PASSED]")


def test_empty_arrays():
    """Test that empty arrays return invalid status."""
    print("\n=== TEST: Empty Arrays ===")

    # Both empty
    x = np.array([])
    y = np.array([])
    x_clean, y_clean, status = align_xy_for_interp(x, y)
    assert not status['valid'], "Empty arrays should be invalid"
    assert x_clean is None and y_clean is None, "Should return None for empty"

    # One empty
    x = np.array([1, 2, 3])
    y = np.array([])
    x_clean, y_clean, status = align_xy_for_interp(x, y)
    assert not status['valid'], "One empty array should be invalid"

    print("[PASSED]")


def test_single_point():
    """Test that single point returns invalid when min_points=2."""
    print("\n=== TEST: Single Point ===")
    x = np.array([1.0])
    y = np.array([10.0])

    x_clean, y_clean, status = align_xy_for_interp(x, y, min_points=2)
    assert not status['valid'], "Single point should be invalid with min_points=2"

    # But valid if min_points=1
    x_clean, y_clean, status = align_xy_for_interp(x, y, min_points=1)
    assert status['valid'], "Single point should be valid with min_points=1"

    print("[PASSED]")


def test_non_monotonic():
    """Test that non-monotonic x values get sorted."""
    print("\n=== TEST: Non-Monotonic X Values ===")
    x = np.array([3, 1, 4, 2, 0])  # Not sorted
    y = np.array([30, 10, 40, 20, 0])

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should be valid after sorting"
    assert 'sorted' in status['actions'], "Should report sorting"
    assert np.all(np.diff(x_clean) > 0), "x should be strictly increasing after sort"

    # Check that y values were reordered correctly with x
    expected_x = np.array([0, 1, 2, 3, 4])
    expected_y = np.array([0, 10, 20, 30, 40])
    np.testing.assert_array_equal(x_clean, expected_x)
    np.testing.assert_array_equal(y_clean, expected_y)

    print("[PASSED]")


def test_duplicate_x_values():
    """Test that duplicate x values get de-duplicated."""
    print("\n=== TEST: Duplicate X Values ===")
    x = np.array([0, 1, 1, 2, 3, 3, 3])  # Duplicates
    y = np.array([10, 20, 25, 30, 40, 45, 50])

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should be valid after deduplication"
    assert 'deduped' in status['actions'], "Should report deduplication"
    assert len(x_clean) < len(x), "Should have fewer points after dedup"

    # Check no duplicates remain
    assert len(x_clean) == len(np.unique(x_clean)), "No duplicates should remain"

    print("[PASSED]")


def test_nan_values():
    """Test that NaN values are removed."""
    print("\n=== TEST: NaN Values ===")
    x = np.array([0, 1, 2, np.nan, 4])
    y = np.array([10, 20, np.nan, 40, 50])

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should be valid after removing NaN"
    assert 'removed_nan_inf' in status['actions'], "Should report NaN removal"
    assert not np.any(np.isnan(x_clean)), "No NaN in x_clean"
    assert not np.any(np.isnan(y_clean)), "No NaN in y_clean"

    print("[PASSED]")


def test_inf_values():
    """Test that Inf values are removed."""
    print("\n=== TEST: Inf Values ===")
    x = np.array([0, 1, np.inf, 3, 4])
    y = np.array([10, 20, 30, -np.inf, 50])

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should be valid after removing Inf"
    assert 'removed_nan_inf' in status['actions'], "Should report Inf removal"
    assert not np.any(np.isinf(x_clean)), "No Inf in x_clean"
    assert not np.any(np.isinf(y_clean)), "No Inf in y_clean"

    print("[PASSED]")


def test_scalar_inputs():
    """Test that scalar inputs are handled."""
    print("\n=== TEST: Scalar Inputs ===")
    x = 5.0  # Scalar
    y = 10.0

    x_clean, y_clean, status = align_xy_for_interp(x, y, min_points=1)

    assert status['valid'], "Should handle scalars"
    assert len(x_clean) == 1, "Should have length 1"

    print("[PASSED]")


def test_multi_dimensional_y():
    """Test that multi-dimensional y arrays get raveled."""
    print("\n=== TEST: Multi-Dimensional Y ===")
    x = np.array([0, 1, 2, 3])
    y = np.array([[10, 20, 30, 40]])  # 2D array (1, 4)

    x_clean, y_clean, status = align_xy_for_interp(x, y)

    assert status['valid'], "Should handle 2D y by raveling"
    assert y_clean.ndim == 1, "y should be 1D after raveling"
    assert len(x_clean) == len(y_clean), "Lengths should match"

    print("[PASSED]")


def test_combined_edge_cases():
    """Test combination of multiple edge cases."""
    print("\n=== TEST: Combined Edge Cases ===")
    # Length mismatch + duplicates + NaN + non-monotonic
    x = np.array([3, 1, np.nan, 2, 2, 0])
    y = np.array([30, 10, 25, 20, 0])  # Shorter

    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=True)

    assert status['valid'], "Should handle multiple issues"
    assert len(x_clean) == len(y_clean), "Lengths should match"
    assert np.all(np.isfinite(x_clean)), "No NaN/Inf"
    assert np.all(np.diff(x_clean) > 0), "Strictly increasing"

    print("[PASSED]")


def test_safe_interp1d():
    """Test safe_interp1d wrapper."""
    print("\n=== TEST: safe_interp1d Wrapper ===")
    x = np.array([0, 1, 2, 3])
    y = np.array([10, 20, 30])  # Length mismatch

    # Should auto-align and create interpolator
    interp = safe_interp1d(x, y)

    assert interp is not None, "Should create interpolator despite mismatch"

    # Test interpolation
    y_interp = interp(1.5)
    expected = 25.0  # Linear interpolation between 20 and 30
    assert np.isclose(y_interp, expected), f"Interpolation incorrect: {y_interp} != {expected}"

    print("[PASSED]")


def test_validate_inputs():
    """Test validate_interpolation_inputs quick check."""
    print("\n=== TEST: validate_interpolation_inputs ===")

    # Valid
    x = np.array([0, 1, 2])
    y = np.array([10, 20, 30])
    assert validate_interpolation_inputs(x, y), "Should validate"

    # Empty
    assert not validate_interpolation_inputs([], []), "Empty should fail"

    # Single point with min_points=2
    assert not validate_interpolation_inputs([1], [10], min_points=2), "Single point should fail"

    print("[PASSED]")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Main Test Runner
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("INTERPOLATION UTILITY TEST SUITE")
    print("=" * 60)

    tests = [
        test_length_mismatch,
        test_empty_arrays,
        test_single_point,
        test_non_monotonic,
        test_duplicate_x_values,
        test_nan_values,
        test_inf_values,
        test_scalar_inputs,
        test_multi_dimensional_y,
        test_combined_edge_cases,
        test_safe_interp1d,
        test_validate_inputs
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAILED]: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR]: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
