#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Simulation Worker
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Multiprocessing worker for running simulations in background
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import multiprocessing as mp
import numpy as np
import logging
from ecoevocrm.consumer_resource_system import Community

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def simulation_worker_process(params, data_queue, control_queue):
    """
    Worker function that runs in a separate process to execute the simulation.

    This function creates a Community object based on provided parameters,
    runs the simulation, and streams data back to the main GUI process
    via a multiprocessing queue.

    Args:
        params (dict): Dictionary of simulation parameters
        data_queue (mp.Queue): Queue for sending data to main process
        control_queue (mp.Queue): Queue for receiving control signals (currently unused)
    """
    import os
    import traceback

    # DIAGNOSTIC LOGGING
    print(f"\n[WORKER] simulation_worker_process started: PID={os.getpid()}", flush=True)
    print(f"[WORKER] Received params: T={params.get('T')}, dt={params.get('dt')}, "
          f"num_resources={params.get('num_resources')}", flush=True)

    #------------------------------
    # Define progress callback that puts data into queue
    #------------------------------
    callback_call_count = [0]  # Tracks how many times callback is invoked

    def progress_callback(data):
        """
        Callback function invoked by Community.run() after each integration epoch.

        Attempts to put data into the queue, with a timeout to avoid blocking
        indefinitely if the queue is full.

        Adds lineageIDs to the callback data for stable type identification
        across mutations.
        """
        callback_call_count[0] += 1

        # DIAGNOSTIC LOGGING
        print(f"[WORKER] progress_callback fired: call #{callback_call_count[0]}, "
              f"t_current={data.get('t_current', 'N/A')}", flush=True)

        try:
            # NEW CONTRACT: N_epoch and lineageIDs_epoch are already aligned
            # Worker just passes data through - no reconstruction needed

            lineageIDs_epoch = data.get('lineageIDs_epoch')

            if lineageIDs_epoch is not None:
                # Data already has correct contract: N_epoch.shape[0] == len(lineageIDs_epoch)
                data['lineageIDs'] = lineageIDs_epoch  # Rename for GUI compatibility
            else:
                # Fallback for old contract (shouldn't happen after fix)
                print(f"[WORKER]   WARNING: lineageIDs_epoch not provided, using fallback", flush=True)
                data['lineageIDs'] = list(community.type_set.lineageIDs)

            # Throttle logging
            if not hasattr(progress_callback, '_worker_count'):
                progress_callback._worker_count = 0
            progress_callback._worker_count += 1

            if progress_callback._worker_count % 20 == 0:
                N_epoch = data.get('N_epoch')
                t_epoch = data.get('t_epoch')
                print(f"[WORKER]   Pass-through #{progress_callback._worker_count}: "
                      f"lineages={len(data['lineageIDs'])}, "
                      f"N_epoch shape={N_epoch.shape if N_epoch is not None else 'None'}, "
                      f"t_epoch len={len(t_epoch) if hasattr(t_epoch, '__len__') else 1}",
                      flush=True)

            data_queue.put(data, timeout=0.5)
        except Exception as e:
            print(f"[WORKER]   ERROR in progress_callback: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()

    #------------------------------
    # Wrap simulation in try-except to catch and report errors
    #------------------------------
    try:
        #------------------------------
        # Extract parameters from dictionary
        #------------------------------
        T = params['T']
        dt = params.get('dt', None)
        num_types = params.get('num_types', None)
        num_resources = params.get('num_resources', None)
        mutation_rate = params.get('mutation_rate', 1e-9)
        decay_rate = params.get('decay_rate', 1)
        cost_baseline = params.get('cost_baseline', 0)
        carrying_capacity = params.get('carrying_capacity', 1e9)
        trait_pattern = params.get('trait_pattern', None)

        # Support suppression-specific parameters
        cost_interaction = params.get('cost_interaction', None)
        cost_landscape = params.get('cost_landscape', None)
        cost_pertrait = params.get('cost_pertrait', 0)

        # Handle influx_rate (now just a simple array or scalar, not interpolator)
        influx_rate = params.get('influx_rate', 1)

        # Validate if it's an array
        if isinstance(influx_rate, np.ndarray):
            if len(influx_rate) != num_resources:
                error_msg = (
                    f"[SimulationWorker] Influx array length mismatch: "
                    f"expected {num_resources}, got {len(influx_rate)}"
                )
                logging.error(error_msg)
                data_queue.put({'status': 'error', 'message': error_msg})
                return
            logging.info(
                f"[SimulationWorker] Using constant influx: shape={influx_rate.shape}"
            )

        #------------------------------
        # Build traits matrix based on selected pattern (or use provided)
        #------------------------------
        if 'traits' in params:
            # Use provided traits (e.g., from suppression_config)
            traits = params['traits']
        elif trait_pattern == 'single_trait':
            # Single trait: only first resource utilized by first type
            traits = np.zeros((num_types, num_resources))
            traits[0, 0] = 1.0
        elif trait_pattern == 'all_resources':
            # All resources: each type utilizes all resources equally
            traits = np.ones((num_types, num_resources)) / num_resources
        else:  # random
            # Random: random trait values, normalized so each type sums to 1
            traits = np.random.rand(num_types, num_resources)
            traits = traits / traits.sum(axis=1, keepdims=True)

        #------------------------------
        # Initialize population abundances (N_init)
        #------------------------------
        N_init = params.get('N_init', np.ones(traits.shape[0]))

        #------------------------------
        # Initialize resource levels (R_init)
        #------------------------------
        R_init = params.get('R_init', np.ones(num_resources if num_resources else traits.shape[1]))

        #------------------------------
        # Create Community object
        #------------------------------
        community_params = {
            'traits': traits,
            'N_init': N_init,
            'R_init': R_init,
            'mutation_rate': mutation_rate,
            'influx_rate': influx_rate,
            'decay_rate': decay_rate,
            'cost_baseline': cost_baseline,
            'carrying_capacity': carrying_capacity,
            'resource_dynamics_mode': 'explicit',  # Use explicit resource dynamics
            'print_events': False  # Don't print mutation events to console in GUI mode
        }

        # Add suppression-specific parameters if provided
        if cost_interaction is not None:
            community_params['cost_interaction'] = cost_interaction
        if cost_landscape is not None:
            community_params['cost_landscape'] = cost_landscape
        if cost_pertrait is not None:
            community_params['cost_pertrait'] = cost_pertrait

        # DIAGNOSTIC LOGGING
        print(f"[WORKER] Creating Community object...", flush=True)

        community = Community(**community_params)

        print(f"[WORKER] Community created successfully", flush=True)
        print(f"[WORKER] Starting community.run(T={T}, dt={dt})...", flush=True)

        #------------------------------
        # Run simulation with progress callback
        #------------------------------
        community.run(T=T, dt=dt, progress_callback=progress_callback)

        # DIAGNOSTIC LOGGING
        print(f"[WORKER] community.run() completed: final t={community.t}, "
              f"callback called {callback_call_count[0]} times", flush=True)

        #------------------------------
        # Send completion signal to main process
        #------------------------------
        data_queue.put({'status': 'completed', 't_final': community.t})

    except Exception as e:
        #------------------------------
        # Send error message to main process
        #------------------------------
        error_msg = f"[WORKER] FATAL ERROR: {type(e).__name__}: {e}"
        print(error_msg, flush=True)

        import traceback
        full_traceback = traceback.format_exc()
        print(full_traceback, flush=True)

        data_queue.put({'status': 'error', 'message': full_traceback})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SimulationWorker:
    """
    Manager class for simulation worker process.

    Handles starting, stopping, and communicating with the background
    simulation process.
    """

    def __init__(self):
        """
        Initialize the simulation worker manager.
        """
        self.process = None
        self.data_queue = None
        self.control_queue = None

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def start(self, parameters):
        """
        Start a simulation in a background process.

        Args:
            parameters (dict): Dictionary of simulation parameters
        """
        #------------------------------
        # Create communication queues
        #------------------------------
        # maxsize=100 prevents unbounded memory growth if GUI can't keep up
        self.data_queue = mp.Queue(maxsize=100)
        self.control_queue = mp.Queue()

        #------------------------------
        # Create and start worker process
        #------------------------------
        self.process = mp.Process(
            target=simulation_worker_process,
            args=(parameters, self.data_queue, self.control_queue)
        )
        self.process.start()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def stop(self):
        """
        Stop the running simulation.

        Attempts graceful termination, then forces termination if needed.
        """
        if self.process and self.process.is_alive():
            #------------------------------
            # Send stop signal (for future implementation)
            #------------------------------
            # self.control_queue.put('STOP')

            #------------------------------
            # Terminate the process
            #------------------------------
            self.process.terminate()
            self.process.join(timeout=2.0)

            #------------------------------
            # Force kill if still alive
            #------------------------------
            if self.process.is_alive():
                self.process.kill()
                self.process.join()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def is_running(self):
        """
        Check if the simulation process is still running.

        Returns:
            bool: True if process is alive, False otherwise
        """
        return self.process is not None and self.process.is_alive()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_data(self):
        """
        Retrieve all available data from the queue (non-blocking).

        This method is called periodically by the GUI's timer to poll for
        new data from the simulation.

        Returns:
            list: List of data dictionaries from the queue
        """
        data_chunks = []

        #------------------------------
        # Empty the queue of all available items
        #------------------------------
        while not self.data_queue.empty():
            try:
                data_chunks.append(self.data_queue.get_nowait())
            except:
                break

        return data_chunks

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
