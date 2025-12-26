# EcoEvoCRM Real-time GUI

A PyQt5-based graphical user interface for real-time visualization of EcoEvoCRM evolutionary dynamics simulations.

## Features

- **Interactive Parameter Input**: Configure 10 essential simulation parameters through an intuitive GUI
- **Real-time Visualization**: Watch biomass evolution as the simulation runs
- **Non-blocking Execution**: Simulation runs in a separate process, keeping the UI responsive
- **Efficient Data Streaming**: Integration epochs stream data to the plot for smooth animation

## Installation

1. Install the core EcoEvoCRM package (if not already installed):
```bash
cd C:\Users\Djordje\Desktop\ECOEVO3\ecoevocrm-main
pip install -e .
```

2. Install GUI dependencies:
```bash
pip install -r requirements_gui.txt
```

## Usage

### Starting the Application

Run the GUI application from the command line:

```bash
python -m ecoevocrm.app
```

Or from within the ecoevocrm-main directory:

```bash
cd src
python -m ecoevocrm.app
```

### Using the Interface

1. **Set Parameters**: Adjust the 10 simulation parameters in the left panel:
   - `T`: Total simulation time (default: 1e6)
   - `dt`: Time step for saving data (default: 1e3)
   - `num_types`: Number of initial microbial types (default: 1)
   - `num_resources`: Number of resource types (default: 10)
   - `mutation_rate`: Per-trait mutation rate (default: 1e-9)
   - `influx_rate`: Resource influx rate (default: 1.0)
   - `decay_rate`: Resource decay rate (default: 1.0)
   - `cost_baseline`: Baseline metabolic cost (default: 0.1)
   - `carrying_capacity`: Population carrying capacity (default: 1e9)
   - `trait_pattern`: How to initialize traits (Single trait/All resources/Random)

2. **Run Simulation**: Click the "Run Simulation" button to start

3. **Watch in Real-time**: The plot on the right will update as the simulation progresses, showing total biomass over time

4. **Stop if Needed**: Click "Stop" to terminate the simulation early

5. **Completion**: A dialog will appear when the simulation finishes successfully

### Tips for Testing

For quick testing with fast results:
- Set `T` to a smaller value like `1000` or `10000`
- Set `dt` to `10` or `100`
- Keep `num_types` at 1 and `num_resources` at 10

For realistic evolutionary dynamics:
- Use default values (T=1e6, dt=1e3)
- Experiment with different trait patterns
- Try different mutation rates (e.g., 1e-8 for faster evolution)

## Architecture

### File Structure

```
src/ecoevocrm/
├── consumer_resource_system.py  # Modified to add progress_callback
├── app.py                       # Application entry point
└── gui/
    ├── __init__.py             # Package initializer
    ├── main_window.py          # Main application window
    ├── parameter_panel.py      # Parameter input widgets
    ├── plot_widget.py          # Real-time matplotlib plot
    ├── simulation_worker.py    # Multiprocessing worker
    └── utils.py                # Utility functions
```

### Data Flow

1. User inputs parameters in the GUI
2. Clicks "Run" → parameters sent to worker process
3. Worker process creates `Community` object and calls `run()`
4. After each integration epoch, `progress_callback` sends data to queue
5. Main GUI process polls queue every 100ms
6. Plot updates incrementally with new data
7. On completion, worker sends status message

## Troubleshooting

### "No module named 'PyQt5'"

Install PyQt5:
```bash
pip install PyQt5
```

### Simulation Not Starting

Check that:
- All parameters are valid positive numbers
- PyQt5 and matplotlib are installed
- The ecoevocrm package is properly installed

### Plot Not Updating

- The simulation may be running very slowly with large parameter values
- Try reducing `T` to test with faster simulations
- Check the status label for error messages

### Process Terminated Unexpectedly

- This may happen with invalid parameter combinations
- Check the error message in the dialog
- Verify that trait patterns match the number of types/resources

## Future Enhancements

Planned features for future versions:
- Play/pause controls during simulation
- Speed adjustment
- Multiple plots (resources, diversity metrics)
- Save/load parameter presets
- Export results to CSV
- Per-type abundance visualization
- Phylogenetic tree display

## Backend Modifications

The only modification to the core simulation code is the addition of an optional `progress_callback` parameter to `Community.run()`:

```python
def run(self, T, dt=None, ..., progress_callback=None):
```

This callback receives data after each integration epoch and is used to stream data to the GUI. When `progress_callback=None` (default), the simulation runs exactly as before, ensuring full backward compatibility.

## Contact

For issues or questions about the GUI, please refer to the main EcoEvoCRM repository.
