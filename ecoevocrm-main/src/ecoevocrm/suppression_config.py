#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Suppression Model Configuration
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Encapsulates all parameters for the suppression model simulation
# from notebook: 2025-10-06_explore-group-suppression.ipynb
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
import logging
import ecoevocrm.utils as utils

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_suppression_params(quick_test=False):
    """
    Returns all parameters for the suppression model simulation
    exactly as specified in 2025-10-06_explore-group-suppression.ipynb

    Args:
        quick_test (bool): If True, use shorter simulation time (T=1e4, dt=100)
                          for rapid validation. Default: False (full T=1e6)

    Returns:
        dict: Complete parameter dictionary for Community initialization
              and simulation run parameters
    """

    #------------------------------
    # Traits: 16 resources with alternating pattern
    #------------------------------
    num_resources = 16
    traits_init = np.zeros(num_resources)
    traits_init[::-2] = 1  # Alternating pattern: [0,1,0,1,0,1,...]
    traits_init = traits_init.reshape((1, num_resources))

    #------------------------------
    # Costs
    #------------------------------
    cost_baseline = 0.1
    cost_pertrait = 0.5

    # Interaction matrix J (Tikhonov sigmoid ordered)
    J_0 = 0.3
    J_NSTAR = 16
    DELTA = 4
    J_SEED  = 1
    J_ORDER_POWER = 20

    J = utils.random_matrix(
        (num_resources, num_resources),
        'tikhonov_sigmoid_ordered',
        args={'J_0': J_0, 'n_star': J_NSTAR, 'delta': DELTA},
        triangular=True,
        diagonal=0,
        shuffle=True,
        order_power=J_ORDER_POWER,
        seed=J_SEED
    )

    # Cost suppressions via cost_landscape
    cost_suppressions = {
        '11**************': 10.0,  # First two traits suppressed
        '**************11': 10.0   # Last two traits suppressed
    }

    #------------------------------
    # Environment: Brownian motion influx
    #------------------------------
    # Quick test mode: faster validation (10-30 seconds instead of 30 minutes)
    if quick_test:
        T_total = 1e4   # 10,000 time units
        dt_env  = 100   # Larger timestep for faster sampling
        logging.info("[suppression_config] Quick test mode: T=1e4, dt=100")
    else:
        T_total = 1e6   # 1 million time units (full simulation)
        dt_env  = 1e3   # Standard timestep
        logging.info("[suppression_config] Full mode: T=1e6, dt=1e3")

    #------------------------------
    # Constant per-resource influx (simplified from Brownian series)
    #------------------------------
    # Each resource gets influx rate = 1.0 (can be made configurable later)
    influx_rate = np.ones(num_resources)  # Shape: (16,)

    logging.info(
        f"[suppression_config] Using constant influx: shape={influx_rate.shape}, "
        f"values=[{influx_rate[0]:.2f}, ..., {influx_rate[-1]:.2f}]"
    )

    #------------------------------
    # Initial conditions
    #------------------------------
    N_init = np.ones(1)
    R_init = np.ones(num_resources)

    #------------------------------
    # Simulation parameters
    #------------------------------
    k = 1e9      # carrying_capacity
    m = 1e-9     # mutation_rate
    delta = 1    # decay_rate

    #------------------------------
    # Return complete parameter dictionary
    #------------------------------
    return {
        # Community initialization parameters
        'traits': traits_init,
        'N_init': N_init,
        'R_init': R_init,
        'cost_baseline': cost_baseline,
        'cost_pertrait': cost_pertrait,
        'cost_interaction': J,
        'cost_landscape': cost_suppressions,
        'carrying_capacity': k,
        'mutation_rate': m,
        'decay_rate': delta,

        # Influx (constant per-resource)
        'influx_rate': influx_rate,      # Simple constant array (16,)

        # Simulation run parameters
        'T': T_total,
        'dt': dt_env,

        # Metadata
        'num_resources': num_resources,
        'num_types_init': 1,
    }

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
