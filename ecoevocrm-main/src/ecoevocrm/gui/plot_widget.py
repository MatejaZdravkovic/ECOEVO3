#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Real-time Plot Widget
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Matplotlib canvas embedded in PyQt5 for real-time biomass visualization
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BiomassPlotWidget(FigureCanvasQTAgg):
    """
    Real-time biomass plot widget using matplotlib embedded in PyQt5.

    This widget displays total biomass evolution over time with efficient
    incremental updates for smooth animation during simulation.
    """

    def __init__(self, parent=None, window_size=None):
        """
        Initialize the biomass plot widget.

        Args:
            parent: Parent Qt widget (optional)
            window_size (float): Time window to display (None = show all)
        """
        #------------------------------
        # Create matplotlib figure and axes
        #------------------------------
        self.fig = Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        #------------------------------
        # Initialize data storage
        #------------------------------
        self.t_data = []
        self.biomass_data = []

        #------------------------------
        # Window/zoom settings
        #------------------------------
        self.window_size = window_size  # None = show all, else show last N time units
        self.all_t_data = []            # Complete data history (for scrubbing/zoom)
        self.all_biomass_data = []

        #------------------------------
        # Create plot line
        #------------------------------
        self.line, = self.ax.plot([], [], 'b-', linewidth=1.5, label='Total Biomass')

        #------------------------------
        # Configure plot appearance
        #------------------------------
        self.ax.set_xlabel('Time', fontsize=12)
        self.ax.set_ylabel('Total Biomass', fontsize=12)
        self.ax.set_title('Real-time Biomass Evolution', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.legend(loc='best')

        #------------------------------
        # Set tight layout
        #------------------------------
        self.fig.tight_layout()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def update_data(self, t_new, biomass_new):
        """
        Incrementally add new data and update the plot.

        This method efficiently appends new data points without redrawing
        the entire plot, ensuring smooth real-time updates.

        Args:
            t_new: New time point(s) - can be scalar or array
            biomass_new: New biomass value(s) - can be scalar or array
        """
        #------------------------------
        # Append new data to storage
        #------------------------------
        if isinstance(t_new, np.ndarray):
            # Multiple data points provided
            self.t_data.extend(t_new.tolist())
            self.biomass_data.extend(biomass_new.tolist())
        else:
            # Single data point provided
            self.t_data.append(t_new)
            self.biomass_data.append(biomass_new)

        #------------------------------
        # Update plot line data (efficient - just updates data, no redraw)
        #------------------------------
        self.line.set_data(self.t_data, self.biomass_data)

        #------------------------------
        # Adjust axes limits to show all data
        #------------------------------
        self.ax.relim()
        self.ax.autoscale_view(tight=False)

        #------------------------------
        # Redraw the canvas
        #------------------------------
        self.draw()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def add_streaming_point(self, t, biomass):
        """
        Add single data point for smooth streaming animation.

        This method is optimized for 60 FPS updates - it adds one point at a time
        and uses draw_idle() for efficient rendering. If window_size is set,
        only the most recent data within the window is displayed.

        Args:
            t (float): Simulation time
            biomass (float): Biomass value at time t
        """
        #------------------------------
        # Store in complete history
        #------------------------------
        self.all_t_data.append(t)
        self.all_biomass_data.append(biomass)

        #------------------------------
        # Update visible window
        #------------------------------
        if self.window_size is not None:
            # Windowed mode - show only recent data
            visible_indices = [i for i, t_val in enumerate(self.all_t_data)
                             if t_val >= t - self.window_size]
            visible_t = [self.all_t_data[i] for i in visible_indices]
            visible_biomass = [self.all_biomass_data[i] for i in visible_indices]
        else:
            # Show all data
            visible_t = self.all_t_data
            visible_biomass = self.all_biomass_data

        #------------------------------
        # Update plot line
        #------------------------------
        self.line.set_data(visible_t, visible_biomass)

        #------------------------------
        # Adjust axes limits
        #------------------------------
        self.ax.relim()
        self.ax.autoscale_view(tight=False)

        #------------------------------
        # Efficient redraw (doesn't block)
        #------------------------------
        self.draw_idle()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def set_window_size(self, size):
        """
        Change visualization window size (zoom in/out).

        Args:
            size (float or None): Time window to display (None = show all)
        """
        self.window_size = size

        # Trigger redraw with new window
        if len(self.all_t_data) > 0:
            # Redisplay with new window
            t_current = self.all_t_data[-1]
            self.add_streaming_point(t_current, self.all_biomass_data[-1])

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def clear_plot(self):
        """
        Reset the plot for a new simulation.

        Clears all data and redraws an empty plot.
        """
        #------------------------------
        # Clear data storage
        #------------------------------
        self.t_data = []
        self.biomass_data = []
        self.all_t_data = []
        self.all_biomass_data = []

        #------------------------------
        # Clear plot line
        #------------------------------
        self.line.set_data([], [])

        #------------------------------
        # Redraw empty plot
        #------------------------------
        self.draw()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
