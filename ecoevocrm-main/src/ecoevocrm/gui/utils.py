#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM GUI Utilities
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Helper functions for the GUI application
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def validate_positive_float(text):
    """
    Validate that a text string represents a positive float value.

    Args:
        text (str): Input string to validate

    Returns:
        bool: True if text is a valid positive float, False otherwise
    """
    try:
        val = float(text)
        return val > 0
    except ValueError:
        return False

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def validate_positive_int(text):
    """
    Validate that a text string represents a positive integer value.

    Args:
        text (str): Input string to validate

    Returns:
        bool: True if text is a valid positive integer, False otherwise
    """
    try:
        val = int(text)
        return val > 0
    except ValueError:
        return False

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def parse_array_input(text, expected_length):
    """
    Parse comma-separated array input or single value.
    Single values are broadcast to arrays of expected length.

    Args:
        text (str): Comma-separated values or single value
        expected_length (int): Expected array length

    Returns:
        np.ndarray or None: Parsed array, or None if parsing failed
    """
    try:
        values = [float(x.strip()) for x in text.split(',')]
        if len(values) == 1:
            # Single value - broadcast to array
            return np.full(expected_length, values[0])
        elif len(values) == expected_length:
            return np.array(values)
        else:
            return None
    except:
        return None

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
