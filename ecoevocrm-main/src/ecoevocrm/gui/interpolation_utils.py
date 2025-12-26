#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Interpolation Utilities
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Defensive helpers for safe array interpolation in streaming simulation data
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
import logging

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global debug flag (toggle for detailed logging)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
DEBUG_INTERPOLATION = False

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def align_xy_for_interp(x, y, min_points=2, debug=False, context=""):
    """
    Safely align x and y arrays for interpolation.

    This function handles all common edge cases that cause scipy.interpolate.interp1d
    and np.interp to fail when working with streaming simulation data:

    - Length mismatch between x and y
    - Empty arrays
    - Single data point (insufficient for interpolation)
    - Non-monotonic x values (unsorted or decreasing)
    - Duplicate x values
    - NaN or Inf values in either array

    Args:
        x: Array-like x values (will be converted to 1D numpy array)
        y: Array-like y values (will be converted to 1D numpy array)
        min_points (int): Minimum number of points required for interpolation (default: 2)
        debug (bool): Enable detailed logging (default: False)
        context (str): Optional context string for debug messages (e.g., "biomass_interp")

    Returns:
        tuple: (x_aligned, y_aligned, status_dict) where:
            - x_aligned: Clean 1D numpy array, or None if validation failed
            - y_aligned: Clean 1D numpy array, or None if validation failed
            - status_dict: Dictionary with keys:
                - 'valid' (bool): True if arrays are ready for interpolation
                - 'message' (str): Human-readable status message
                - 'x_len_in' (int): Original x length
                - 'y_len_in' (int): Original y length
                - 'x_len_out' (int): Final x length (0 if invalid)
                - 'y_len_out' (int): Final y length (0 if invalid)
                - 'actions' (list): List of actions taken (e.g., ['truncated', 'deduped'])

    Examples:
        >>> x = np.array([0, 1, 2, 3])
        >>> y = np.array([10, 20, 30])  # Length mismatch
        >>> x_clean, y_clean, status = align_xy_for_interp(x, y)
        >>> status['valid']
        True
        >>> len(x_clean) == len(y_clean) == 3
        True

        >>> x = np.array([])
        >>> y = np.array([])
        >>> x_clean, y_clean, status = align_xy_for_interp(x, y)
        >>> status['valid']
        False
    """
    use_debug = debug or DEBUG_INTERPOLATION
    actions = []

    #------------------------------
    # Step 1: Convert to 1D numpy arrays
    #------------------------------
    try:
        x_arr = np.asarray(x).ravel()
        y_arr = np.asarray(y).ravel()
    except Exception as e:
        status = {
            'valid': False,
            'message': f'Failed to convert to arrays: {e}',
            'x_len_in': 0,
            'y_len_in': 0,
            'x_len_out': 0,
            'y_len_out': 0,
            'actions': ['conversion_failed']
        }
        if use_debug:
            logging.warning(f"[INTERP:{context}] FAILED - {status['message']}")
        return None, None, status

    x_len_in = len(x_arr)
    y_len_in = len(y_arr)

    #------------------------------
    # Step 2: Handle empty arrays
    #------------------------------
    if x_len_in == 0 or y_len_in == 0:
        status = {
            'valid': False,
            'message': f'Empty array(s): x_len={x_len_in}, y_len={y_len_in}',
            'x_len_in': x_len_in,
            'y_len_in': y_len_in,
            'x_len_out': 0,
            'y_len_out': 0,
            'actions': ['empty_arrays']
        }
        if use_debug:
            logging.warning(f"[INTERP:{context}] FAILED - {status['message']}")
        return None, None, status

    #------------------------------
    # Step 3: Truncate to minimum length if mismatch
    #------------------------------
    if x_len_in != y_len_in:
        min_len = min(x_len_in, y_len_in)
        x_arr = x_arr[:min_len]
        y_arr = y_arr[:min_len]
        actions.append('truncated')
        if use_debug:
            logging.info(f"[INTERP:{context}] Truncated from x={x_len_in}, y={y_len_in} to {min_len}")

    #------------------------------
    # Step 4: Remove NaN and Inf values
    #------------------------------
    valid_mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    if not np.all(valid_mask):
        x_arr = x_arr[valid_mask]
        y_arr = y_arr[valid_mask]
        actions.append('removed_nan_inf')
        if use_debug:
            logging.info(f"[INTERP:{context}] Removed NaN/Inf values, now {len(x_arr)} points")

    #------------------------------
    # Step 5: Check minimum points requirement
    #------------------------------
    if len(x_arr) < min_points:
        status = {
            'valid': False,
            'message': f'Insufficient points: {len(x_arr)} < {min_points}',
            'x_len_in': x_len_in,
            'y_len_in': y_len_in,
            'x_len_out': len(x_arr),
            'y_len_out': len(y_arr),
            'actions': actions + ['insufficient_points']
        }
        if use_debug:
            logging.warning(f"[INTERP:{context}] FAILED - {status['message']}")
        return None, None, status

    #------------------------------
    # Step 6: Sort by x if not monotonically increasing
    #------------------------------
    if len(x_arr) > 1:
        # Check if strictly increasing
        if not np.all(np.diff(x_arr) > 0):
            # Need to sort
            sort_idx = np.argsort(x_arr)
            x_arr = x_arr[sort_idx]
            y_arr = y_arr[sort_idx]
            actions.append('sorted')
            if use_debug:
                logging.info(f"[INTERP:{context}] Sorted arrays by x values")

    #------------------------------
    # Step 7: Remove duplicate x values (keep first occurrence)
    #------------------------------
    if len(x_arr) > 1:
        _, unique_idx = np.unique(x_arr, return_index=True)
        if len(unique_idx) < len(x_arr):
            # Duplicates found - keep only unique
            unique_idx = np.sort(unique_idx)  # Preserve order
            x_arr = x_arr[unique_idx]
            y_arr = y_arr[unique_idx]
            actions.append('deduped')
            if use_debug:
                logging.info(f"[INTERP:{context}] Removed duplicates, now {len(x_arr)} points")

    #------------------------------
    # Step 8: Final validation
    #------------------------------
    if len(x_arr) < min_points:
        status = {
            'valid': False,
            'message': f'After cleanup: {len(x_arr)} < {min_points}',
            'x_len_in': x_len_in,
            'y_len_in': y_len_in,
            'x_len_out': len(x_arr),
            'y_len_out': len(y_arr),
            'actions': actions + ['insufficient_after_cleanup']
        }
        if use_debug:
            logging.warning(f"[INTERP:{context}] FAILED - {status['message']}")
        return None, None, status

    #------------------------------
    # Success!
    #------------------------------
    status = {
        'valid': True,
        'message': 'Arrays aligned successfully',
        'x_len_in': x_len_in,
        'y_len_in': y_len_in,
        'x_len_out': len(x_arr),
        'y_len_out': len(y_arr),
        'actions': actions if actions else ['no_changes']
    }

    if use_debug:
        actions_str = ', '.join(actions) if actions else 'no changes'
        logging.info(
            f"[INTERP:{context}] SUCCESS - "
            f"x_len={x_len_in}->{len(x_arr)}, y_len={y_len_in}->{len(y_arr)}, "
            f"actions=[{actions_str}]"
        )

    return x_arr, y_arr, status

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def validate_interpolation_inputs(x, y, min_points=2):
    """
    Quick validation check for interpolation inputs.

    Use this for fast pre-checks before calling align_xy_for_interp() or
    interpolation functions directly.

    Args:
        x: Array-like x values
        y: Array-like y values
        min_points (int): Minimum number of points required

    Returns:
        bool: True if inputs appear valid, False otherwise
    """
    try:
        x_arr = np.asarray(x).ravel()
        y_arr = np.asarray(y).ravel()

        if len(x_arr) < min_points or len(y_arr) < min_points:
            return False

        # Check for any finite values
        if not np.any(np.isfinite(x_arr)) or not np.any(np.isfinite(y_arr)):
            return False

        return True
    except:
        return False

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def safe_interp1d(x, y, kind='linear', bounds_error=False, fill_value='extrapolate', **kwargs):
    """
    Wrapper around scipy.interpolate.interp1d with automatic array alignment.

    This function automatically applies align_xy_for_interp() before creating
    the interpolator, making it safe to use with streaming simulation data.

    Args:
        x: Array-like x values
        y: Array-like y values
        kind (str): Interpolation kind ('linear', 'nearest', 'cubic', etc.)
        bounds_error (bool): Whether to raise error on out-of-bounds (default: False)
        fill_value: Value to use for out-of-bounds points (default: 'extrapolate')
        **kwargs: Additional arguments passed to scipy.interpolate.interp1d

    Returns:
        scipy.interpolate.interp1d object, or None if alignment failed

    Examples:
        >>> x = [0, 1, 2, 3]
        >>> y = [10, 20, 30]  # Length mismatch - will be auto-corrected
        >>> interp = safe_interp1d(x, y)
        >>> if interp is not None:
        ...     value = interp(1.5)
    """
    from scipy.interpolate import interp1d

    # Align arrays
    x_clean, y_clean, status = align_xy_for_interp(x, y, debug=DEBUG_INTERPOLATION, context="safe_interp1d")

    if not status['valid']:
        logging.warning(f"[safe_interp1d] Failed to align arrays: {status['message']}")
        return None

    # Create interpolator
    try:
        return interp1d(x_clean, y_clean, kind=kind, bounds_error=bounds_error,
                       fill_value=fill_value, **kwargs)
    except Exception as e:
        logging.error(f"[safe_interp1d] Failed to create interpolator: {e}")
        return None

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def safe_np_interp(x_new, x_data, y_data, context=""):
    """
    Wrapper around np.interp with automatic array alignment.

    Args:
        x_new: Points to interpolate at
        x_data: Known x values
        y_data: Known y values
        context (str): Optional context for debug messages

    Returns:
        np.ndarray: Interpolated values, or array of NaN if alignment failed
    """
    # Align data arrays
    x_clean, y_clean, status = align_xy_for_interp(
        x_data, y_data,
        debug=DEBUG_INTERPOLATION,
        context=f"np_interp:{context}"
    )

    if not status['valid']:
        logging.warning(f"[safe_np_interp:{context}] Failed to align: {status['message']}")
        # Return NaN array of same shape as x_new
        x_new_arr = np.asarray(x_new).ravel()
        return np.full_like(x_new_arr, np.nan, dtype=float)

    # Perform interpolation
    try:
        return np.interp(x_new, x_clean, y_clean)
    except Exception as e:
        logging.error(f"[safe_np_interp:{context}] Interpolation failed: {e}")
        x_new_arr = np.asarray(x_new).ravel()
        return np.full_like(x_new_arr, np.nan, dtype=float)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
