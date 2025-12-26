#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Main Window
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Main application window that orchestrates the GUI components
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QSplitter, QMessageBox, QSlider)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import time

from .parameter_panel import ParameterPanel
from .plot_widget import BiomassPlotWidget
from .simulation_worker import SimulationWorker
from .animation_controller import AnimationController

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MainWindow(QMainWindow):
    """
    Main application window for EcoEvoCRM real-time simulator.

    Provides a GUI interface with parameter inputs, control buttons,
    and real-time biomass visualization.
    """

    def __init__(self):
        """
        Initialize the main window and all GUI components.
        """
        super().__init__()

        #------------------------------
        # Configure window properties
        #------------------------------
        self.setWindowTitle("EcoEvoCRM Real-time Simulator")
        self.setGeometry(100, 100, 1200, 700)

        #------------------------------
        # Create main widgets
        #------------------------------
        self.param_panel = ParameterPanel()
        self.plot_widget = BiomassPlotWidget()
        self.worker = SimulationWorker()

        #------------------------------
        # Create animation controller
        #------------------------------
        self.animation_controller = AnimationController()
        self.last_frame_time = None

        #------------------------------
        # Create control buttons
        #------------------------------
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self.on_run_clicked)
        self.run_button.setMinimumHeight(40)
        run_button_font = QFont()
        run_button_font.setPointSize(11)
        run_button_font.setBold(True)
        self.run_button.setFont(run_button_font)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setFont(run_button_font)

        #------------------------------
        # Create playback controls
        #------------------------------
        self.play_pause_button = QPushButton("Pause")
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.setMinimumHeight(35)

        self.speed_label = QLabel("Speed: 1.0x")
        self.speed_label.setAlignment(Qt.AlignCenter)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)  # Log scale: 0.1x to 10x
        self.speed_slider.setValue(10)  # 1.0x default
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        self.speed_slider.setEnabled(False)

        #------------------------------
        # Create zoom controls
        #------------------------------
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.on_zoom_in)
        self.zoom_in_button.setEnabled(False)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.on_zoom_out)
        self.zoom_out_button.setEnabled(False)

        self.zoom_reset_button = QPushButton("Fit All")
        self.zoom_reset_button.clicked.connect(self.on_zoom_reset)
        self.zoom_reset_button.setEnabled(False)

        #------------------------------
        # Create status label
        #------------------------------
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #f0f0f0; "
                                       "border: 1px solid #ccc; border-radius: 5px; }")

        #------------------------------
        # Layout - Left panel (parameters + controls)
        #------------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        left_layout.addWidget(self.param_panel)
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

        # Zoom controls section
        zoom_label = QLabel("Zoom Controls")
        zoom_label.setAlignment(Qt.AlignCenter)
        zoom_label.setFont(QFont("Arial", 9, QFont.Bold))
        left_layout.addWidget(zoom_label)

        zoom_buttons_layout = QHBoxLayout()
        zoom_buttons_layout.addWidget(self.zoom_in_button)
        zoom_buttons_layout.addWidget(self.zoom_out_button)
        left_layout.addLayout(zoom_buttons_layout)
        left_layout.addWidget(self.zoom_reset_button)

        left_layout.addWidget(self.status_label)
        left_layout.addStretch()

        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(350)

        #------------------------------
        # Layout - Main layout with splitter
        #------------------------------
        main_widget = QWidget()
        main_layout = QHBoxLayout()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.plot_widget)
        splitter.setStretchFactor(0, 1)  # Left panel takes 1 part
        splitter.setStretchFactor(1, 3)  # Plot takes 3 parts

        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)

        #------------------------------
        # Set central widget
        #------------------------------
        self.setCentralWidget(main_widget)

        #------------------------------
        # Create dual timers for streaming animation
        #------------------------------
        # Data timer: Poll backend for new data chunks (100ms)
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.poll_data)

        # Animation timer: Smooth playback at ~60 FPS (16ms)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_frame)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_run_clicked(self):
        """
        Handle 'Run Simulation' button click.

        Extracts parameters, starts the simulation worker, and begins
        polling for data updates.
        """
        #------------------------------
        # Get parameters from input panel
        #------------------------------
        try:
            params = self.param_panel.get_parameters()
        except Exception as e:
            #------------------------------
            # Show error dialog if parameter extraction fails
            #------------------------------
            QMessageBox.critical(self, "Parameter Error",
                               f"Error reading parameters:\n{str(e)}")
            return

        #------------------------------
        # Clear previous plot and reset animation
        #------------------------------
        self.plot_widget.clear_plot()
        self.animation_controller.reset()
        self.last_frame_time = None

        #------------------------------
        # Start simulation worker process
        #------------------------------
        self.worker.start(params)

        #------------------------------
        # Start both timers
        #------------------------------
        self.data_timer.start(100)      # Poll backend every 100ms
        self.animation_timer.start(16)  # Animate at ~60 FPS

        #------------------------------
        # Update UI state
        #------------------------------
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        self.speed_slider.setEnabled(True)
        self.zoom_in_button.setEnabled(True)
        self.zoom_out_button.setEnabled(True)
        self.zoom_reset_button.setEnabled(True)
        self.param_panel.set_enabled(False)
        self.status_label.setText("Status: Running...")
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #d4edda; "
                                       "border: 1px solid #c3e6cb; border-radius: 5px; "
                                       "color: #155724; }")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_stop_clicked(self):
        """
        Handle 'Stop' button click.

        Stops the simulation worker and resets the UI to idle state.
        """
        #------------------------------
        # Stop worker process
        #------------------------------
        self.worker.stop()

        #------------------------------
        # Stop both timers
        #------------------------------
        self.data_timer.stop()
        self.animation_timer.stop()

        #------------------------------
        # Reset UI state
        #------------------------------
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.play_pause_button.setEnabled(False)
        self.speed_slider.setEnabled(False)
        self.zoom_in_button.setEnabled(False)
        self.zoom_out_button.setEnabled(False)
        self.zoom_reset_button.setEnabled(False)
        self.param_panel.set_enabled(True)
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #fff3cd; "
                                       "border: 1px solid #ffeaa7; border-radius: 5px; "
                                       "color: #856404; }")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def poll_data(self):
        """
        Poll the data queue and add new data to animation buffer.

        This method is called periodically by the data timer (100ms).
        It retrieves all available data from the worker's queue and
        feeds it to the animation controller's buffer.
        """
        #------------------------------
        # Get all available data chunks from queue
        #------------------------------
        data_chunks = self.worker.get_data()

        #------------------------------
        # Process each data chunk
        #------------------------------
        for chunk in data_chunks:
            #------------------------------
            # Check for status messages (completion or error)
            #------------------------------
            if 'status' in chunk:
                if chunk['status'] == 'completed':
                    #------------------------------
                    # Simulation completed successfully
                    #------------------------------
                    self.on_stop_clicked()
                    self.status_label.setText(f"Status: Completed (t={chunk['t_final']:.2e})")
                    self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #d1ecf1; "
                                                   "border: 1px solid #bee5eb; border-radius: 5px; "
                                                   "color: #0c5460; }")

                    #------------------------------
                    # Show completion message
                    #------------------------------
                    QMessageBox.information(self, "Simulation Complete",
                                          f"Simulation completed successfully!\n"
                                          f"Final time: {chunk['t_final']:.2e}")

                elif chunk['status'] == 'error':
                    #------------------------------
                    # Simulation encountered an error
                    #------------------------------
                    self.on_stop_clicked()
                    self.status_label.setText(f"Status: Error")
                    self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #f8d7da; "
                                                   "border: 1px solid #f5c6cb; border-radius: 5px; "
                                                   "color: #721c24; }")

                    #------------------------------
                    # Show error dialog
                    #------------------------------
                    QMessageBox.critical(self, "Simulation Error",
                                       f"An error occurred during simulation:\n{chunk['message']}")

            #------------------------------
            # Process normal data update (epoch completed)
            #------------------------------
            elif 'epoch_completed' in chunk:
                #------------------------------
                # Add data to animation controller buffer
                #------------------------------
                self.animation_controller.add_data_chunk(
                    chunk['t_epoch'],
                    chunk['biomass_epoch']
                )

        #------------------------------
        # Check if process died unexpectedly
        #------------------------------
        if not self.worker.is_running() and self.data_timer.isActive():
            self.on_stop_clicked()
            self.status_label.setText("Status: Process terminated unexpectedly")
            self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #f8d7da; "
                                           "border: 1px solid #f5c6cb; border-radius: 5px; "
                                           "color: #721c24; }")

            #------------------------------
            # Show error dialog
            #------------------------------
            QMessageBox.warning(self, "Process Terminated",
                              "The simulation process terminated unexpectedly.")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def animate_frame(self):
        """
        Smooth animation update at ~60 FPS.

        This method is called by the animation timer (16ms).
        It advances the animation time and updates the plot with
        interpolated data from the buffer.
        """
        #------------------------------
        # Calculate elapsed real time since last frame
        #------------------------------
        current_time = time.time()
        if self.last_frame_time is None:
            self.last_frame_time = current_time
            return

        real_time_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time

        #------------------------------
        # Get next frame from animation controller
        #------------------------------
        frame_data = self.animation_controller.get_next_frame(real_time_delta)

        if frame_data is not None:
            t_sim, biomass = frame_data

            #------------------------------
            # Update plot with streaming point
            #------------------------------
            self.plot_widget.add_streaming_point(t_sim, biomass)

            #------------------------------
            # Update status label with three time scales
            #------------------------------
            buffer_status = self.animation_controller.get_buffer_status()
            self.status_label.setText(
                f"Animation: t={t_sim:.2e} | "
                f"Integration: t={self.animation_controller.integration_time:.2e} | "
                f"Buffer: {buffer_status['buffer_gap']:.0f} ({buffer_status['health']})"
            )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def toggle_play_pause(self):
        """Toggle animation playback between play and pause."""
        if self.animation_controller.is_playing:
            self.animation_controller.pause()
            self.play_pause_button.setText("Play")
        else:
            self.animation_controller.play()
            self.play_pause_button.setText("Pause")
            self.last_frame_time = None  # Reset frame timing

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_speed_changed(self, value):
        """
        Handle speed slider change.

        Args:
            value (int): Slider value (1-100, log scale)
        """
        # Log scale: 1-100 -> 0.1x to 10x
        speed = 0.1 * (10 ** ((value - 1) / 99 * 2))
        self.animation_controller.set_speed(speed)
        self.speed_label.setText(f"Speed: {speed:.1f}x")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_zoom_in(self):
        """Zoom in (reduce window size)."""
        current = self.plot_widget.window_size
        if current is None:
            # Currently showing all data
            total_time = self.animation_controller.integration_time
            if total_time > 0:
                self.plot_widget.set_window_size(total_time * 0.5)
        else:
            self.plot_widget.set_window_size(current * 0.5)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_zoom_out(self):
        """Zoom out (increase window size)."""
        current = self.plot_widget.window_size
        if current is not None:
            new_size = current * 2
            total_time = self.animation_controller.integration_time
            if new_size >= total_time:
                self.plot_widget.set_window_size(None)  # Show all
            else:
                self.plot_widget.set_window_size(new_size)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def on_zoom_reset(self):
        """Reset zoom to show all data."""
        self.plot_widget.set_window_size(None)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def closeEvent(self, event):
        """
        Handle window close event.

        Ensures the simulation worker is properly stopped before closing.

        Args:
            event: Close event
        """
        #------------------------------
        # Stop worker if running
        #------------------------------
        if self.worker.is_running():
            reply = QMessageBox.question(self, 'Simulation Running',
                                        'A simulation is currently running. Stop it and exit?',
                                        QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
