#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Suppression Model Window
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Main window for real-time suppression model visualization
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QMessageBox, QSlider,
                             QGroupBox, QFormLayout, QDoubleSpinBox, QFrame,
                             QCheckBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import time
import logging

from .multi_type_plot_widget import MultiTypePlotWidget
from .plot_widget import BiomassPlotWidget
from .simulation_worker import SimulationWorker
from .animation_controller import AnimationController
from ecoevocrm.suppression_config import get_suppression_params

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SuppressionWindow(QMainWindow):
    """
    Main window for Suppression Model real-time visualization.

    Features:
    - Hardcoded suppression model parameters (no input panel needed)
    - Multi-type abundance plot (top) + total biomass plot (bottom)
    - Real-time streaming with playback speed control
    - Three timescale status display
    """

    def __init__(self):
        """
        Initialize the suppression window and all GUI components.
        """
        super().__init__()

        #------------------------------
        # Configure window properties
        #------------------------------
        self.setWindowTitle("EcoEvoCRM - Suppression Model")
        self.setGeometry(100, 100, 1400, 900)

        #------------------------------
        # Create plot widgets
        #------------------------------
        self.multi_type_plot = MultiTypePlotWidget()
        self.biomass_plot = BiomassPlotWidget()

        #------------------------------
        # Create simulation worker and controller
        #------------------------------
        self.worker = SimulationWorker()
        self.animation_controller = AnimationController()
        self.last_frame_time = None

        #------------------------------
        # Create control buttons
        #------------------------------
        button_font = QFont()
        button_font.setPointSize(11)
        button_font.setBold(True)

        self.run_button = QPushButton("Run Suppression Model Simulation")
        self.run_button.clicked.connect(self.on_run_clicked)
        self.run_button.setMinimumHeight(50)
        self.run_button.setFont(button_font)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setFont(button_font)

        #------------------------------
        # Create playback controls
        #------------------------------
        self.play_pause_button = QPushButton("Pause")
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.setMinimumHeight(35)

        self.speed_label = QLabel("Speed: Manual (1.0×)")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setFont(QFont("Arial", 10))

        self.speed_slider = QSlider(Qt.Horizontal)
        # Expanded range: -60 to +80 for 0.25x to 100x
        # -60 → 10^(-1.5) ≈ 0.316 → clamp to 0.25
        # 0 → 10^0 = 1.0
        # +80 → 10^2 = 100.0
        self.speed_slider.setRange(-60, 80)
        self.speed_slider.setValue(0)  # 1.0x default
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        self.speed_slider.setEnabled(False)

        #------------------------------
        # Auto speed mode toggle
        #------------------------------
        self.auto_speed_checkbox = QCheckBox("Auto Speed")
        self.auto_speed_checkbox.setChecked(False)  # Start in manual mode
        self.auto_speed_checkbox.stateChanged.connect(self.on_auto_speed_toggled)
        self.auto_speed_checkbox.setEnabled(False)  # Enable when simulation starts
        self.auto_speed_checkbox.setToolTip(
            "Enable automatic timescale-aware playback speed.\n"
            "Speed adapts based on simulation time and data density."
        )

        #------------------------------
        # Create status label (three timescales)
        #------------------------------
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(
            "QLabel { padding: 15px; background-color: #f0f0f0; "
            "border: 2px solid #ccc; border-radius: 5px; }"
        )

        #------------------------------
        # Create parameter input group
        #------------------------------
        param_group = QGroupBox("Cost Parameters")
        param_layout = QFormLayout()

        # cost_baseline: 0.01 - 1.0, default 0.1
        self.cost_baseline_input = QDoubleSpinBox()
        self.cost_baseline_input.setRange(0.01, 1.0)
        self.cost_baseline_input.setSingleStep(0.01)
        self.cost_baseline_input.setValue(0.1)
        self.cost_baseline_input.setDecimals(2)
        param_layout.addRow("Baseline Cost:", self.cost_baseline_input)

        # cost_pertrait: 0.1 - 5.0, default 0.5
        self.cost_pertrait_input = QDoubleSpinBox()
        self.cost_pertrait_input.setRange(0.1, 5.0)
        self.cost_pertrait_input.setSingleStep(0.1)
        self.cost_pertrait_input.setValue(0.5)
        self.cost_pertrait_input.setDecimals(1)
        param_layout.addRow("Per-Trait Cost:", self.cost_pertrait_input)

        # Suppression value: 0 - 20, default 10
        self.suppression_value_input = QDoubleSpinBox()
        self.suppression_value_input.setRange(0.0, 20.0)
        self.suppression_value_input.setSingleStep(1.0)
        self.suppression_value_input.setValue(10.0)
        self.suppression_value_input.setDecimals(1)
        param_layout.addRow("Suppression Value:", self.suppression_value_input)

        param_group.setLayout(param_layout)
        self.param_group = param_group  # Store reference for layout

        #------------------------------
        # Layout - Left panel (controls)
        #------------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)  # Add 12px spacing between widgets
        left_layout.setContentsMargins(10, 10, 10, 10)  # 10px margins

        left_layout.addWidget(self.param_group)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator)

        left_layout.addWidget(self.run_button)
        left_layout.addWidget(self.stop_button)

        # Playback controls section
        playback_label = QLabel("Playback Controls")
        playback_label.setAlignment(Qt.AlignCenter)
        playback_label.setFont(QFont("Arial", 9, QFont.Bold))
        left_layout.addWidget(playback_label)
        left_layout.addWidget(self.play_pause_button)
        left_layout.addWidget(self.speed_label)
        left_layout.addWidget(self.speed_slider)

        # Speed hints
        speed_hint = QLabel("<- Slower  |  Faster ->")
        speed_hint.setAlignment(Qt.AlignCenter)
        speed_hint.setFont(QFont("Arial", 8))
        speed_hint.setStyleSheet("QLabel { color: #666; }")
        left_layout.addWidget(speed_hint)

        #------------------------------
        # Visualization window controls
        #------------------------------
        viz_label = QLabel("View Controls")
        viz_label.setAlignment(Qt.AlignCenter)
        viz_label.setFont(QFont("Arial", 9, QFont.Bold))
        left_layout.addWidget(viz_label)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        self.zoom_in_button = QPushButton("🔍+ Zoom In")
        self.zoom_out_button = QPushButton("🔍- Zoom Out")
        self.zoom_in_button.clicked.connect(lambda: self.animation_controller.zoom_in())
        self.zoom_out_button.clicked.connect(lambda: self.animation_controller.zoom_out())
        self.zoom_in_button.setEnabled(False)
        self.zoom_out_button.setEnabled(False)
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.zoom_out_button)
        left_layout.addLayout(zoom_layout)

        # Scrub controls
        scrub_layout = QHBoxLayout()
        self.scrub_back_button = QPushButton("◀ Back")
        self.scrub_forward_button = QPushButton("Forward ▶")
        self.scrub_back_button.clicked.connect(lambda: self.animation_controller.scrub_backward(10.0))
        self.scrub_forward_button.clicked.connect(lambda: self.animation_controller.scrub_forward(10.0))
        self.scrub_back_button.setEnabled(False)
        self.scrub_forward_button.setEnabled(False)
        scrub_layout.addWidget(self.scrub_back_button)
        scrub_layout.addWidget(self.scrub_forward_button)
        left_layout.addLayout(scrub_layout)

        # Snap to live button
        self.snap_live_button = QPushButton("📍 Snap to Live")
        self.snap_live_button.clicked.connect(lambda: self.animation_controller.snap_to_live_edge())
        self.snap_live_button.setEnabled(False)
        left_layout.addWidget(self.snap_live_button)

        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)  # +50px for parameter inputs

        #------------------------------
        # Layout - Right panel (plots)
        #------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Add plots (multi-type on top, biomass on bottom)
        right_layout.addWidget(self.multi_type_plot, stretch=2)
        right_layout.addWidget(self.biomass_plot, stretch=1)

        right_panel.setLayout(right_layout)

        #------------------------------
        # Main layout (horizontal split)
        #------------------------------
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        #------------------------------
        # Setup timers
        #------------------------------
        # Timer for polling simulation data from worker
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.on_poll_timer)
        self.poll_timer.setInterval(16)  # ~60 FPS polling

        # Timer for animation updates (smooth playback)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.on_animation_timer)
        self.animation_timer.setInterval(16)  # ~60 FPS rendering

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_run_clicked(self):
        """
        Start the suppression model simulation.

        Gets parameters from suppression_config and launches worker process.
        """
        #------------------------------
        # Get suppression model parameters
        #------------------------------
        params = get_suppression_params()

        #------------------------------
        # Override with user input values
        #------------------------------
        params['cost_baseline'] = self.cost_baseline_input.value()
        params['cost_pertrait'] = self.cost_pertrait_input.value()

        # Update cost_landscape suppressions with user value
        suppression_val = self.suppression_value_input.value()
        params['cost_landscape'] = {
            '11**************': suppression_val,
            '**************11': suppression_val
        }

        logging.info(
            f"[SuppressionWindow] Using parameters: "
            f"cost_baseline={params['cost_baseline']:.2f}, "
            f"cost_pertrait={params['cost_pertrait']:.2f}, "
            f"suppression={suppression_val:.1f}"
        )

        # DIAGNOSTIC LOGGING
        print(f"\n[GUI] on_run_clicked: T={params['T']}, dt={params.get('dt')}, "
              f"num_resources={params.get('num_resources', 'N/A')}, "
              f"num_types={params.get('num_types_init', 'N/A')}", flush=True)
        print(f"[GUI] Starting worker process...", flush=True)

        #------------------------------
        # Reset animation controller and plots
        #------------------------------
        self.animation_controller.reset()
        self.multi_type_plot.clear_plot()
        # Note: biomass_plot doesn't have clear method, would need to add it
        # For now, it will just overlay new data

        #------------------------------
        # Start simulation worker
        #------------------------------
        self.worker.start(params)

        # DIAGNOSTIC LOGGING
        if self.worker.process:
            print(f"[GUI] Worker process spawned: PID={self.worker.process.pid}", flush=True)

        #------------------------------
        # Start timers
        #------------------------------
        self.poll_timer.start()
        self.animation_timer.start()
        self.last_frame_time = time.time()

        #------------------------------
        # Update UI state
        #------------------------------
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        # Enable slider only if auto mode is not active
        self.speed_slider.setEnabled(not self.auto_speed_checkbox.isChecked())
        self.auto_speed_checkbox.setEnabled(True)  # Enable auto toggle
        self.zoom_in_button.setEnabled(True)
        self.zoom_out_button.setEnabled(True)
        self.scrub_back_button.setEnabled(True)
        self.scrub_forward_button.setEnabled(True)
        self.snap_live_button.setEnabled(True)

        # Disable parameter inputs during simulation
        self.cost_baseline_input.setEnabled(False)
        self.cost_pertrait_input.setEnabled(False)
        self.suppression_value_input.setEnabled(False)

        self.update_status_label()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_stop_clicked(self):
        """
        Stop the running simulation.
        """
        #------------------------------
        # Stop worker and timers
        #------------------------------
        self.worker.stop()
        self.poll_timer.stop()
        self.animation_timer.stop()

        #------------------------------
        # Update UI state
        #------------------------------
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.play_pause_button.setEnabled(False)
        self.speed_slider.setEnabled(False)
        self.zoom_in_button.setEnabled(False)
        self.zoom_out_button.setEnabled(False)
        self.scrub_back_button.setEnabled(False)
        self.scrub_forward_button.setEnabled(False)
        self.snap_live_button.setEnabled(False)

        # Re-enable parameter inputs after stop
        self.cost_baseline_input.setEnabled(True)
        self.cost_pertrait_input.setEnabled(True)
        self.suppression_value_input.setEnabled(True)

        self.status_label.setText("Status: Stopped")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_poll_timer(self):
        """
        Poll for new data from simulation worker.

        Called ~60 times per second to check for new simulation data.
        """
        #------------------------------
        # Check if simulation is still running
        #------------------------------
        if not self.worker.is_running():
            self.on_simulation_completed()
            return

        #------------------------------
        # Get new data chunks from worker
        #------------------------------
        data_chunks = self.worker.get_data()

        # DIAGNOSTIC LOGGING
        if data_chunks:
            print(f"[GUI] on_poll_timer: Received {len(data_chunks)} data chunks", flush=True)
            for i, data in enumerate(data_chunks):
                keys = list(data.keys())
                print(f"[GUI]   Chunk {i}: keys={keys}", flush=True)
                if 't_epoch' in data:
                    t_epoch = data['t_epoch']
                    if hasattr(t_epoch, '__len__'):
                        print(f"[GUI]   t_epoch: len={len(t_epoch)}, "
                              f"range=[{t_epoch[0]:.2e}, {t_epoch[-1]:.2e}]", flush=True)

        for data in data_chunks:
            if 'status' in data:
                # Handle status messages
                if data['status'] == 'completed':
                    self.on_simulation_completed()
                elif data['status'] == 'error':
                    # IMPROVED ERROR DISPLAY
                    error_msg = data.get('message', 'Unknown error')
                    print(f"[GUI] WORKER ERROR:\n{error_msg}", flush=True)
                    QMessageBox.critical(self, "Simulation Error",
                                        f"Worker process error:\n\n{error_msg}")
                    self.on_stop_clicked()
            else:
                # Handle simulation data
                self.process_data_chunk(data)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def process_data_chunk(self, data):
        """
        Process a chunk of simulation data.

        Adds data to animation controller buffer.

        Args:
            data (dict): Data dictionary from progress_callback
        """
        #------------------------------
        # Extract data
        #------------------------------
        t_epoch = data['t_epoch']
        N_epoch = data['N_epoch']
        biomass_epoch = data['biomass_epoch']
        lineageIDs = data.get('lineageIDs', [])

        # DIAGNOSTIC LOGGING
        import numpy as np
        print(f"[GUI] process_data_chunk: t_epoch shape={np.shape(t_epoch)}, "
              f"N_epoch shape={np.shape(N_epoch)}, "
              f"biomass_epoch shape={np.shape(biomass_epoch)}, "
              f"num_lineages={len(lineageIDs)}", flush=True)

        #------------------------------
        # Add to animation controller
        #------------------------------
        # Add biomass data (for biomass plot)
        self.animation_controller.add_data_chunk(t_epoch, biomass_epoch)

        # Add multi-type data (for multi-type plot)
        if len(lineageIDs) > 0:
            self.animation_controller.add_multi_type_data_chunk(
                t_epoch, N_epoch, lineageIDs
            )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_animation_timer(self):
        """
        Update animation frame.

        Called ~60 times per second to advance animation smoothly.
        """
        #------------------------------
        # Calculate real time delta since last frame
        #------------------------------
        current_time = time.time()
        if self.last_frame_time is None:
            real_time_delta = 0.016  # Default to 16ms
        else:
            real_time_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time

        #------------------------------
        # Get next animation frame from controller
        #------------------------------
        frame_data = self.animation_controller.get_next_frame(real_time_delta)

        if frame_data is not None:
            t_anim, biomass_anim = frame_data

            # Update biomass plot
            self.biomass_plot.update_data(t_anim, biomass_anim)

            # Update multi-type plot using controller's interpolated data
            self.multi_type_plot.update_from_controller(self.animation_controller)

        #------------------------------
        # Throttle speed label updates to ~5-10 Hz (not every frame)
        #------------------------------
        if not hasattr(self, '_label_update_counter'):
            self._label_update_counter = 0

        self._label_update_counter += 1

        # Update label every 6 frames (~10 Hz at 60 FPS)
        if self._label_update_counter >= 6:
            self._label_update_counter = 0

            if self.auto_speed_checkbox.isChecked():
                current_speed = self.animation_controller.get_current_effective_speed()
                self.speed_label.setText(f"Speed: Auto ({current_speed:.2f}×)")

        #------------------------------
        # Update status display
        #------------------------------
        self.update_status_label()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def toggle_play_pause(self):
        """
        Toggle between play and pause states.
        """
        if self.animation_controller.is_playing:
            self.animation_controller.pause()
            self.play_pause_button.setText("Play")
        else:
            self.animation_controller.play()
            self.play_pause_button.setText("Pause")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_speed_changed(self, value):
        """
        Update animation speed based on slider.

        Only applies when in manual mode (auto unchecked).

        Args:
            value (int): Slider value (-60 to +80)
        """
        # Convert slider value to speed multiplier (logarithmic scale)
        # Expanded range: 0.25x to 100x
        speed = 10 ** (value / 40.0)
        speed = max(0.25, min(speed, 100.0))

        # Update controller (only affects manual mode)
        self.animation_controller.set_manual_speed(speed)

        # Update label only if in manual mode
        if not self.auto_speed_checkbox.isChecked():
            self.speed_label.setText(f"Speed: Manual ({speed:.2f}×)")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_auto_speed_toggled(self, state):
        """
        Handle auto speed checkbox state change.

        Args:
            state (int): Qt.Checked or Qt.Unchecked
        """
        from PyQt5.QtCore import Qt

        if state == Qt.Checked:
            # Enable auto mode
            self.animation_controller.enable_auto_speed()
            self.speed_slider.setEnabled(False)  # Disable slider in auto mode

            # Update label to show auto mode
            auto_speed = self.animation_controller.get_current_effective_speed()
            self.speed_label.setText(f"Speed: Auto ({auto_speed:.2f}×)")
        else:
            # Disable auto mode (manual)
            self.animation_controller.disable_auto_speed()
            self.speed_slider.setEnabled(True)  # Enable slider in manual mode

            # Update label to show manual mode
            manual_speed = self.animation_controller.get_current_effective_speed()
            self.speed_label.setText(f"Speed: Manual ({manual_speed:.2f}×)")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def update_status_label(self):
        """
        Update status label with three timescales.

        Shows:
        - Animation time (current playback position)
        - Integration time (latest data received)
        - Buffer gap (health indicator)
        """
        anim_time = self.animation_controller.animation_time
        integ_time = self.animation_controller.integration_time
        buffer_status = self.animation_controller.get_buffer_status()

        buffer_gap = buffer_status['buffer_gap']
        health = buffer_status['health']

        # Color-code by health
        if health == 'healthy':
            color = '#4CAF50'  # Green
        elif health == 'low':
            color = '#FF9800'  # Orange
        else:  # critical
            color = '#F44336'  # Red

        status_text = (
            f"<b>Animation:</b> t={anim_time:.2e}<br>"
            f"<b>Integration:</b> t={integ_time:.2e}<br>"
            f"<span style='color: {color};'><b>Buffer:</b> {buffer_gap:.2e} ({health})</span>"
        )

        self.status_label.setText(status_text)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_simulation_completed(self):
        """
        Handle simulation completion.
        """
        self.poll_timer.stop()

        # Keep animation timer running to finish playback
        # It will stop when animation catches up to integration

        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        QMessageBox.information(
            self,
            "Simulation Complete",
            "The simulation has finished. Animation will continue until all data is displayed."
        )

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
