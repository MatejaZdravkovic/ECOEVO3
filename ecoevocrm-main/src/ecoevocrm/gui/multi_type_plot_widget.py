#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Multi-Type Abundance Plot Widget
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Matplotlib canvas for visualizing abundances of multiple evolving types
# with stable lineage-based coloring and mutation event markers
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MultiTypePlotWidget(FigureCanvasQTAgg):
    """
    Real-time abundance plot for multiple evolving types.

    Features:
    - Dynamic line creation as new types appear (mutations)
    - Stable colors based on lineageID (genealogy-aware)
    - Mutation event markers (vertical dashed lines)
    - Legend management (shows top abundant types)
    """

    def __init__(self, parent=None, max_types_to_plot=50, window_size=None):
        """
        Initialize the multi-type abundance plot widget.

        Args:
            parent: Parent Qt widget (optional)
            max_types_to_plot (int): Maximum number of types to assign colors to
            window_size (float): Time window to display (None = show all)
        """
        #------------------------------
        # Create matplotlib figure and axes
        #------------------------------
        self.fig = Figure(figsize=(10, 7))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)

        #------------------------------
        # LineageID color mapping
        #------------------------------
        self.lineage_id_map = {}       # lineageID -> color_index (stable mapping)
        self.type_lines = {}            # lineageID -> matplotlib Line2D object
        self.type_data = {}             # lineageID -> {'t': [], 'N': []}

        #------------------------------
        # Mutation event markers
        #------------------------------
        self.mutation_markers = []      # List of vertical line artists
        self.last_plotted_mutation_idx = 0  # Track which mutations we've plotted

        #------------------------------
        # Color palette (pre-generate stable colors)
        #------------------------------
        self.max_types = max_types_to_plot
        self.colors = self._generate_color_palette(max_types_to_plot)

        #------------------------------
        # Window/zoom settings
        #------------------------------
        self.window_size = window_size

        #------------------------------
        # Configure plot appearance
        #------------------------------
        self.ax.set_xlabel('Time', fontsize=12)
        self.ax.set_ylabel('Abundance', fontsize=12)
        self.ax.set_title('Multi-Type Abundance Evolution', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_yscale('log')  # Log scale for large abundance ranges

        #------------------------------
        # Set tight layout
        #------------------------------
        self.fig.tight_layout()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _generate_color_palette(self, num_colors):
        """
        Generate visually distinct colors for types.

        Uses matplotlib colormaps to create distinguishable colors.

        Args:
            num_colors (int): Number of colors to generate

        Returns:
            np.ndarray: Array of RGB colors
        """
        # Use tab20 colormap (20 colors) extended with hsv for more
        if num_colors <= 20:
            return plt.cm.tab20(np.linspace(0, 1, num_colors))
        else:
            # Combine tab20 with turbo for larger numbers
            colors1 = plt.cm.tab20(np.linspace(0, 1, 20))
            colors2 = plt.cm.turbo(np.linspace(0, 1, num_colors - 20))
            return np.vstack([colors1, colors2])

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def assign_color(self, lineage_id):
        """
        Assign a stable color to a lineageID.

        Colors are assigned based on order of first appearance (genealogy).

        Args:
            lineage_id (str): Lineage ID

        Returns:
            tuple: RGBA color
        """
        if lineage_id not in self.lineage_id_map:
            # New lineage - assign next color
            color_idx = len(self.lineage_id_map) % len(self.colors)
            self.lineage_id_map[lineage_id] = color_idx

        color_idx = self.lineage_id_map[lineage_id]
        return self.colors[color_idx]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def update_data(self, t_new, N_by_lineage, mutation_occurred=False):
        """
        Add new data point and update plots.

        Args:
            t_new (float): Simulation time
            N_by_lineage (dict): Dict {lineageID: abundance}
            mutation_occurred (bool): If True, add mutation marker
        """
        #------------------------------
        # Update each type's line
        #------------------------------
        for lineage_id, abundance in N_by_lineage.items():
            # Initialize data storage for new lineage
            if lineage_id not in self.type_data:
                self.type_data[lineage_id] = {'t': [], 'N': []}

            # Append data
            self.type_data[lineage_id]['t'].append(t_new)
            self.type_data[lineage_id]['N'].append(max(abundance, 1e-10))  # Avoid log(0)

            # Create line if it doesn't exist
            if lineage_id not in self.type_lines:
                color = self.assign_color(lineage_id)
                line, = self.ax.plot(
                    [], [],
                    color=color,
                    linewidth=1.5,
                    label=f'Type {lineage_id}',
                    alpha=0.8
                )
                self.type_lines[lineage_id] = line

            # Update line data with validation
            line = self.type_lines[lineage_id]
            t_data = self.type_data[lineage_id]['t']
            N_data = self.type_data[lineage_id]['N']

            # Validate lengths match
            if len(t_data) != len(N_data):
                min_len = min(len(t_data), len(N_data))
                logging.warning(
                    f"[MultiTypePlotWidget.update_data] Length mismatch for lineage {lineage_id}: "
                    f"t={len(t_data)}, N={len(N_data)}, truncating to {min_len}"
                )
                t_data = t_data[:min_len]
                N_data = N_data[:min_len]
                # Update stored data to prevent repeated warnings
                self.type_data[lineage_id]['t'] = t_data
                self.type_data[lineage_id]['N'] = N_data

            line.set_data(t_data, N_data)

        #------------------------------
        # Add mutation marker if needed
        #------------------------------
        if mutation_occurred:
            vline = self.ax.axvline(
                t_new,
                color='red',
                linestyle='--',
                alpha=0.5,
                linewidth=1,
                label='Mutation' if len(self.mutation_markers) == 0 else ''
            )
            self.mutation_markers.append(vline)

        #------------------------------
        # Update axes limits
        #------------------------------
        self.ax.relim()
        self.ax.autoscale_view()

        #------------------------------
        # Update legend (show top 10 types only to avoid clutter)
        #------------------------------
        self._update_legend()

        #------------------------------
        # Redraw canvas
        #------------------------------
        self.draw_idle()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def update_from_controller(self, animation_controller):
        """
        Update plot using data from AnimationController.

        This method retrieves interpolated multi-type abundance data
        and checks for new mutation events.

        Args:
            animation_controller (AnimationController): Controller with buffered data
        """
        #------------------------------
        # Get current animation time
        #------------------------------
        t_anim = animation_controller.animation_time

        if t_anim == 0:
            return  # No data yet

        #------------------------------
        # Get interpolated abundances at current time
        #------------------------------
        N_by_lineage = animation_controller._interpolate_multi_type_abundance(t_anim)

        if not N_by_lineage:
            return  # No data

        #------------------------------
        # Check for new mutation events since last update
        #------------------------------
        mutation_occurred = False
        if len(animation_controller.mutation_events) > self.last_plotted_mutation_idx:
            # New mutations occurred - mark the most recent one
            mutation_occurred = True
            self.last_plotted_mutation_idx = len(animation_controller.mutation_events)

        #------------------------------
        # Update plot with new data
        #------------------------------
        self.update_data(t_anim, N_by_lineage, mutation_occurred)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _update_legend(self):
        """
        Update legend to show only top abundant types.

        Limits legend entries to avoid clutter when many types exist.
        """
        # Get current abundances for sorting
        current_abundances = {}
        for lineage_id in self.type_data:
            if len(self.type_data[lineage_id]['N']) > 0:
                current_abundances[lineage_id] = self.type_data[lineage_id]['N'][-1]

        # Sort by abundance (descending)
        sorted_lineages = sorted(
            current_abundances.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Show top 10 + mutations in legend
        top_lineages = [lid for lid, _ in sorted_lineages[:10]]

        # Update legend
        handles, labels = self.ax.get_legend_handles_labels()

        # Filter to show only top types and mutation markers
        filtered_handles = []
        filtered_labels = []

        for handle, label in zip(handles, labels):
            if label == 'Mutation':
                filtered_handles.append(handle)
                filtered_labels.append(label)
            else:
                # Extract lineage ID from label "Type X.Y.Z"
                lineage_id = label.replace('Type ', '')
                if lineage_id in top_lineages:
                    filtered_handles.append(handle)
                    filtered_labels.append(label)

        if filtered_handles:
            self.ax.legend(filtered_handles, filtered_labels, loc='best', fontsize=8)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def clear_plot(self):
        """Clear all data and reset plot."""
        self.lineage_id_map = {}
        self.type_lines = {}
        self.type_data = {}
        self.mutation_markers = []
        self.last_plotted_mutation_idx = 0

        # Clear axes
        self.ax.clear()

        # Reconfigure plot appearance
        self.ax.set_xlabel('Time', fontsize=12)
        self.ax.set_ylabel('Abundance', fontsize=12)
        self.ax.set_title('Multi-Type Abundance Evolution', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_yscale('log')

        # Redraw
        self.draw_idle()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
