#!/usr/bin/env python
"""Tests for suppression configuration and influx shape handling"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from ecoevocrm.suppression_config import get_suppression_params


def test_influx_shape_quick():
    params = get_suppression_params(quick_test=True)
    influx_times = params['influx_times']
    influx_values = params['influx_values']
    num_resources = params['num_resources']

    assert influx_values.ndim == 2, "influx_values should be 2D"
    assert influx_values.shape[0] == len(influx_times), "First axis should be time points"
    assert influx_values.shape[1] == num_resources, "Second axis should be resources"


def test_influx_shape_full():
    # Sanity-check the full (non-quick) configuration as well (may be slower)
    params = get_suppression_params(quick_test=False)
    influx_times = params['influx_times']
    influx_values = params['influx_values']
    num_resources = params['num_resources']

    assert influx_values.ndim == 2, "influx_values should be 2D"
    assert influx_values.shape[0] == len(influx_times), "First axis should be time points"
    assert influx_values.shape[1] == num_resources, "Second axis should be resources"
