#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Parameter Panel
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Input widgets for simulation parameters
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from PyQt5.QtWidgets import (QWidget, QFormLayout, QLineEdit, QComboBox,
                             QLabel, QVBoxLayout, QGroupBox)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ParameterPanel(QWidget):
    """
    Parameter input panel for EcoEvoCRM simulations.

    Provides input widgets for 10 essential simulation parameters with
    validation and default values.
    """

    def __init__(self, parent=None):
        """
        Initialize the parameter panel.

        Args:
            parent: Parent Qt widget (optional)
        """
        super().__init__(parent)

        #------------------------------
        # Create main layout
        #------------------------------
        main_layout = QVBoxLayout()

        #------------------------------
        # Create parameter input group
        #------------------------------
        param_group = QGroupBox("Simulation Parameters")
        form = QFormLayout()

        #------------------------------
        # 1. T - Simulation duration
        #------------------------------
        self.T_input = QLineEdit("1e6")
        self.T_input.setValidator(QDoubleValidator(0, 1e12, 10))
        self.T_input.setToolTip("Total simulation time (default: 1e6)")
        form.addRow("T (duration):", self.T_input)

        #------------------------------
        # 2. dt - Time step for saving
        #------------------------------
        self.dt_input = QLineEdit("1e3")
        self.dt_input.setValidator(QDoubleValidator(0, 1e12, 10))
        self.dt_input.setToolTip("Time step for saving trajectories (default: 1e3)")
        form.addRow("dt (timestep):", self.dt_input)

        #------------------------------
        # 3. num_types - Number of initial types
        #------------------------------
        self.num_types_input = QLineEdit("1")
        self.num_types_input.setValidator(QIntValidator(1, 1000))
        self.num_types_input.setToolTip("Number of initial microbial types (default: 1)")
        form.addRow("Number of types:", self.num_types_input)

        #------------------------------
        # 4. num_resources - Number of resources
        #------------------------------
        self.num_resources_input = QLineEdit("10")
        self.num_resources_input.setValidator(QIntValidator(1, 100))
        self.num_resources_input.setToolTip("Number of resource types (default: 10)")
        form.addRow("Number of resources:", self.num_resources_input)

        #------------------------------
        # 5. mutation_rate - Mutation rate
        #------------------------------
        self.mutation_rate_input = QLineEdit("1e-9")
        self.mutation_rate_input.setValidator(QDoubleValidator(0, 1, 20))
        self.mutation_rate_input.setToolTip("Per-trait mutation rate (default: 1e-9)")
        form.addRow("Mutation rate:", self.mutation_rate_input)

        #------------------------------
        # 6. influx_rate - Resource influx rate
        #------------------------------
        self.influx_rate_input = QLineEdit("1.0")
        self.influx_rate_input.setValidator(QDoubleValidator(0, 1e6, 10))
        self.influx_rate_input.setToolTip("Resource influx rate (default: 1.0)")
        form.addRow("Influx rate:", self.influx_rate_input)

        #------------------------------
        # 7. decay_rate - Resource decay rate
        #------------------------------
        self.decay_rate_input = QLineEdit("1.0")
        self.decay_rate_input.setValidator(QDoubleValidator(0, 1e6, 10))
        self.decay_rate_input.setToolTip("Resource decay rate (default: 1.0)")
        form.addRow("Decay rate:", self.decay_rate_input)

        #------------------------------
        # 8. cost_baseline - Baseline metabolic cost
        #------------------------------
        self.cost_baseline_input = QLineEdit("0.1")
        self.cost_baseline_input.setValidator(QDoubleValidator(0, 10, 10))
        self.cost_baseline_input.setToolTip("Baseline metabolic cost (default: 0.1)")
        form.addRow("Cost baseline:", self.cost_baseline_input)

        #------------------------------
        # 9. carrying_capacity - Carrying capacity
        #------------------------------
        self.carrying_capacity_input = QLineEdit("1e9")
        self.carrying_capacity_input.setValidator(QDoubleValidator(1, 1e15, 10))
        self.carrying_capacity_input.setToolTip("Population carrying capacity (default: 1e9)")
        form.addRow("Carrying capacity:", self.carrying_capacity_input)

        #------------------------------
        # 10. trait_pattern - Initial trait pattern
        #------------------------------
        self.trait_pattern = QComboBox()
        self.trait_pattern.addItems(["Single trait", "All resources", "Random"])
        self.trait_pattern.setToolTip("How to initialize trait matrix:\n"
                                      "- Single trait: Only first resource utilized\n"
                                      "- All resources: All resources utilized equally\n"
                                      "- Random: Random trait values")
        form.addRow("Trait pattern:", self.trait_pattern)

        #------------------------------
        # Set form layout in group box
        #------------------------------
        param_group.setLayout(form)

        #------------------------------
        # Add group box to main layout
        #------------------------------
        main_layout.addWidget(param_group)
        main_layout.addStretch()

        #------------------------------
        # Set main layout
        #------------------------------
        self.setLayout(main_layout)

        #------------------------------
        # Store reference to all input widgets for enable/disable
        #------------------------------
        self.input_widgets = [
            self.T_input,
            self.dt_input,
            self.num_types_input,
            self.num_resources_input,
            self.mutation_rate_input,
            self.influx_rate_input,
            self.decay_rate_input,
            self.cost_baseline_input,
            self.carrying_capacity_input,
            self.trait_pattern
        ]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_parameters(self):
        """
        Extract all parameters as a dictionary.

        Returns:
            dict: Dictionary containing all simulation parameters
        """
        #------------------------------
        # Parse trait pattern selection
        #------------------------------
        trait_pattern_text = self.trait_pattern.currentText()
        if trait_pattern_text == "Single trait":
            trait_pattern = "single_trait"
        elif trait_pattern_text == "All resources":
            trait_pattern = "all_resources"
        else:  # Random
            trait_pattern = "random"

        #------------------------------
        # Build and return parameter dictionary
        #------------------------------
        return {
            'T': float(self.T_input.text()),
            'dt': float(self.dt_input.text()),
            'num_types': int(self.num_types_input.text()),
            'num_resources': int(self.num_resources_input.text()),
            'mutation_rate': float(self.mutation_rate_input.text()),
            'influx_rate': float(self.influx_rate_input.text()),
            'decay_rate': float(self.decay_rate_input.text()),
            'cost_baseline': float(self.cost_baseline_input.text()),
            'carrying_capacity': float(self.carrying_capacity_input.text()),
            'trait_pattern': trait_pattern
        }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def set_enabled(self, enabled):
        """
        Enable or disable all parameter inputs.

        Used to prevent parameter changes while simulation is running.

        Args:
            enabled (bool): True to enable inputs, False to disable
        """
        for widget in self.input_widgets:
            widget.setEnabled(enabled)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
