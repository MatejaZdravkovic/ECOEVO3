#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM Animation Controller
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Controls smooth playback of buffered simulation data
# Manages three time scales: integration, animation, and simulation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import numpy as np
from bisect import bisect_left
import time
import logging
from .interpolation_utils import align_xy_for_interp, DEBUG_INTERPOLATION

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AnimationController:
    """
    Controls smooth animation playback from buffered simulation data.

    Manages three critical time scales:
    1. Integration time: Latest data time from backend (how far simulation has computed)
    2. Animation time: Current playback position (where animation is showing)
    3. Simulation time: The time scale shown on plot (can be huge, e.g., T=1e6)

    The controller maintains a buffer of data ahead of the animation position,
    automatically adjusting playback speed to prevent stuttering if the buffer runs low.
    """

    def __init__(self, default_speed=1.0, buffer_critical=100, buffer_low=1000):
        """
        Initialize the animation controller.

        Args:
            default_speed (float): Default animation speed multiplier (1.0 = real-time)
            buffer_critical (float): Critical buffer threshold (slow down dramatically)
            buffer_low (float): Low buffer threshold (moderate slowdown)
        """
        #------------------------------
        # Data buffer storage
        #------------------------------
        self.buffer_times = []          # Sorted list of simulation times
        self.buffer_biomass = []        # Corresponding biomass values

        # Multi-type data storage (for suppression model)
        self.buffer_N_by_lineage = []   # List of dicts: {lineageID: abundance}
        self.current_lineageIDs = []    # Track current lineageIDs
        self.mutation_events = []       # List of times when mutations occurred

        #------------------------------
        # Time tracking
        #------------------------------
        self.animation_time = 0.0       # Current animation playback position
        self.integration_time = 0.0     # Latest time received from backend

        #------------------------------
        # Playback control
        #------------------------------
        self.animation_speed = default_speed  # User-controlled speed multiplier
        self.is_playing = True                # Play/pause state
        self.last_real_time = None            # Wall-clock time for frame timing

        #------------------------------
        # Buffer management thresholds
        #------------------------------
        self.buffer_critical = buffer_critical  # Critical threshold
        self.buffer_low = buffer_low            # Low threshold

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def add_data_chunk(self, t_epoch, biomass_epoch):
        """
        Add new data chunk from backend to buffer.

        Data chunks arrive after each integration epoch. This method stores
        them in sorted order for smooth interpolation during playback.

        Args:
            t_epoch (np.ndarray): Array of simulation times for this epoch
            biomass_epoch (np.ndarray): Corresponding biomass values
        """
        #------------------------------
        # Convert to lists if arrays
        #------------------------------
        if isinstance(t_epoch, np.ndarray):
            t_list = t_epoch.tolist()
            biomass_list = biomass_epoch.tolist()
        else:
            t_list = [t_epoch]
            biomass_list = [biomass_epoch]

        #------------------------------
        # Validate lengths match
        #------------------------------
        if len(t_list) != len(biomass_list):
            min_len = min(len(t_list), len(biomass_list))
            if DEBUG_INTERPOLATION:
                logging.warning(
                    f"[AnimationController.add_data_chunk] Length mismatch: "
                    f"t={len(t_list)}, biomass={len(biomass_list)}, truncating to {min_len}"
                )
            t_list = t_list[:min_len]
            biomass_list = biomass_list[:min_len]

        #------------------------------
        # Add data points to buffer
        #------------------------------
        for t, biomass in zip(t_list, biomass_list):
            # Skip if already exists (shouldn't happen but be safe)
            if t in self.buffer_times:
                continue

            # Insert in sorted order
            idx = bisect_left(self.buffer_times, t)
            self.buffer_times.insert(idx, t)
            self.buffer_biomass.insert(idx, biomass)

            # Initialize buffer_N_by_lineage with empty dict at same index
            self.buffer_N_by_lineage.insert(idx, {})

        #------------------------------
        # Update integration time (latest time we have data for)
        #------------------------------
        if len(self.buffer_times) > 0:
            self.integration_time = self.buffer_times[-1]

        # DIAGNOSTIC LOGGING
        print(f"[AnimCtrl] add_data_chunk: buffer now has {len(self.buffer_times)} points, "
              f"integration_time={self.integration_time:.2e}", flush=True)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_next_frame(self, real_time_delta):
        """
        Get data for next animation frame.

        This is called ~60 times per second to advance the animation smoothly.
        It advances animation_time based on real elapsed time and returns
        interpolated data at the new position.

        Args:
            real_time_delta (float): Elapsed real wall-clock time since last frame (seconds)

        Returns:
            tuple: (t_sim, biomass) at current animation_time, or None if paused or no data
        """
        #------------------------------
        # Return None if paused
        #------------------------------
        if not self.is_playing:
            return None

        #------------------------------
        # Return None if no data in buffer yet
        #------------------------------
        if len(self.buffer_times) == 0:
            return None

        #------------------------------
        # Calculate how much to advance animation time
        #------------------------------
        # real_time_delta: actual elapsed time (e.g., 0.016 seconds for 60 FPS)
        # animation_speed: user control (0.1x to 10x)
        # get_speed_factor(): automatic slowdown if buffer is low

        speed_factor = self.get_speed_factor()
        delta_anim_time = real_time_delta * self.animation_speed * speed_factor

        # Advance animation time
        self.animation_time += delta_anim_time

        #------------------------------
        # Don't advance beyond available data
        #------------------------------
        if self.animation_time > self.integration_time:
            self.animation_time = self.integration_time

        #------------------------------
        # Interpolate data at current animation_time
        #------------------------------
        biomass = self._interpolate_biomass(self.animation_time)

        return (self.animation_time, biomass)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _interpolate_biomass(self, t):
        """
        Interpolate biomass value at a specific time.

        Uses linear interpolation between buffered data points to provide
        smooth animation even when data points are sparse.

        Args:
            t (float): Simulation time to interpolate at

        Returns:
            float: Interpolated biomass value
        """
        #------------------------------
        # Validate buffer has data
        #------------------------------
        if len(self.buffer_times) == 0 or len(self.buffer_biomass) == 0:
            return 0.0

        # Ensure buffer arrays match in length
        if len(self.buffer_times) != len(self.buffer_biomass):
            if DEBUG_INTERPOLATION:
                logging.warning(
                    f"[AnimationController._interpolate_biomass] Buffer length mismatch: "
                    f"times={len(self.buffer_times)}, biomass={len(self.buffer_biomass)}"
                )
            # Use minimum length
            min_len = min(len(self.buffer_times), len(self.buffer_biomass))
            self.buffer_times = self.buffer_times[:min_len]
            self.buffer_biomass = self.buffer_biomass[:min_len]

        #------------------------------
        # Handle edge cases
        #------------------------------
        if t <= self.buffer_times[0]:
            return self.buffer_biomass[0]

        if t >= self.buffer_times[-1]:
            return self.buffer_biomass[-1]

        #------------------------------
        # Find bracketing indices for interpolation
        #------------------------------
        idx = bisect_left(self.buffer_times, t)

        # Linear interpolation between buffer_times[idx-1] and buffer_times[idx]
        t0, t1 = self.buffer_times[idx-1], self.buffer_times[idx]
        y0, y1 = self.buffer_biomass[idx-1], self.buffer_biomass[idx]

        # Avoid division by zero
        if t1 == t0:
            return y0

        alpha = (t - t0) / (t1 - t0)  # Interpolation factor (0 to 1)
        interpolated_biomass = y0 + alpha * (y1 - y0)

        return interpolated_biomass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_speed_factor(self):
        """
        Calculate dynamic speed adjustment based on buffer status.

        This is the key to smooth animation: if the animation is catching up
        to the integration (buffer running low), we automatically slow down
        playback to prevent stuttering.

        Returns:
            float: Speed factor (0.1 to 1.0)
        """
        #------------------------------
        # Calculate buffer gap (how much data ahead we have)
        #------------------------------
        buffer_gap = self.integration_time - self.animation_time

        #------------------------------
        # Apply dynamic speed adjustment
        #------------------------------
        if buffer_gap < self.buffer_critical:
            # Critically low buffer - slow down dramatically
            return 0.1

        elif buffer_gap < self.buffer_low:
            # Low buffer - proportional slowdown
            # Smoothly scale from 0.1 to 1.0 as buffer_gap increases
            proportion = (buffer_gap - self.buffer_critical) / (self.buffer_low - self.buffer_critical)
            return 0.1 + 0.9 * proportion

        else:
            # Healthy buffer - full speed
            return 1.0

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_buffer_status(self):
        """
        Get current buffer status information.

        Returns:
            dict: Buffer status with keys:
                - buffer_gap: Time units ahead animation has data for
                - buffer_size: Number of data points in buffer
                - speed_factor: Current dynamic speed adjustment
                - health: 'healthy', 'low', or 'critical'
        """
        buffer_gap = self.integration_time - self.animation_time
        speed_factor = self.get_speed_factor()

        if buffer_gap >= self.buffer_low:
            health = 'healthy'
        elif buffer_gap >= self.buffer_critical:
            health = 'low'
        else:
            health = 'critical'

        return {
            'buffer_gap': buffer_gap,
            'buffer_size': len(self.buffer_times),
            'speed_factor': speed_factor,
            'health': health
        }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def play(self):
        """Resume animation playback."""
        self.is_playing = True

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def pause(self):
        """Pause animation playback."""
        self.is_playing = False

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def set_speed(self, speed):
        """
        Set animation speed multiplier.

        Args:
            speed (float): Speed multiplier (0.1 = 10x slower, 10 = 10x faster)
        """
        self.animation_speed = max(0.1, min(speed, 10.0))  # Clamp to reasonable range

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def add_multi_type_data_chunk(self, t_epoch, N_epoch, lineageIDs):
        """
        Add multi-type abundance data chunk to buffer.

        Detects mutation events by tracking changes in lineageIDs.

        NEW CONTRACT: N_epoch contains only active types with shape (num_active_types, num_times)
        where num_active_types == len(lineageIDs). Each row in N_epoch corresponds to
        the lineageID at the same index in lineageIDs.

        Args:
            t_epoch (np.ndarray): Array of simulation times for this epoch
            N_epoch (np.ndarray): Abundance matrix (num_active_types × num_times)
            lineageIDs (list): List of lineage IDs corresponding to N_epoch rows
        """
        #------------------------------
        # Build/update global lineageID index mapping for historical tracking
        #------------------------------
        if not hasattr(self, '_lineage_to_global_idx'):
            self._lineage_to_global_idx = {}
            self._global_lineage_list = []

        # Add new lineages to global mapping
        for lid in lineageIDs:
            if lid not in self._lineage_to_global_idx:
                global_idx = len(self._global_lineage_list)
                self._lineage_to_global_idx[lid] = global_idx
                self._global_lineage_list.append(lid)

        #------------------------------
        # Convert to lists if needed
        #------------------------------
        if isinstance(t_epoch, np.ndarray):
            t_list = t_epoch.tolist() if t_epoch.ndim > 0 else [float(t_epoch)]
        else:
            t_list = [t_epoch]

        #------------------------------
        # Validate array dimensions and contract
        #------------------------------
        if N_epoch.ndim > 1:
            expected_time_points = N_epoch.shape[1]
        else:
            expected_time_points = 1

        # VALIDATION: Ensure N_epoch.shape[0] == len(lineageIDs)
        if N_epoch.shape[0] != len(lineageIDs):
            logging.error(
                f"[AnimationController.add_multi_type_data_chunk] CONTRACT VIOLATION: "
                f"N_epoch.shape[0]={N_epoch.shape[0]} != len(lineageIDs)={len(lineageIDs)}"
            )
            # Defensive: truncate to minimum
            min_types = min(N_epoch.shape[0], len(lineageIDs))
            lineageIDs = lineageIDs[:min_types]

        if len(t_list) != expected_time_points:
            min_len = min(len(t_list), expected_time_points)
            if DEBUG_INTERPOLATION:
                logging.warning(
                    f"[AnimationController.add_multi_type_data_chunk] Length mismatch: "
                    f"t={len(t_list)}, N_epoch.shape[1]={expected_time_points}, truncating to {min_len}"
                )
            t_list = t_list[:min_len]

        #------------------------------
        # Detect mutation events (new types appeared)
        #------------------------------
        prev_num_types = len(self.current_lineageIDs)
        new_num_types = len(lineageIDs)

        if new_num_types > prev_num_types and len(t_list) > 0:
            # Mutation occurred! Record the time
            self.mutation_events.append(t_list[-1])

        self.current_lineageIDs = list(lineageIDs)

        #------------------------------
        # Add multi-type data to buffer
        #------------------------------
        for i, t in enumerate(t_list):
            # Find index of this time (should already exist from add_data_chunk)
            if t not in self.buffer_times:
                print(f"[AnimCtrl] WARNING: time {t} not in buffer_times, skipping", flush=True)
                continue

            idx = self.buffer_times.index(t)

            # Update the dict at this index with abundance data
            for type_idx, lineage_id in enumerate(lineageIDs):
                if type_idx < N_epoch.shape[0]:
                    # Bounds check for time index
                    try:
                        if N_epoch.ndim > 1:
                            # Check bounds before indexing
                            if i < N_epoch.shape[1]:
                                abundance = N_epoch[type_idx, i]
                            else:
                                # Index out of bounds - use last available
                                abundance = N_epoch[type_idx, -1]
                                if DEBUG_INTERPOLATION and i == len(t_list) - 1:
                                    logging.warning(
                                        f"[AnimationController.add_multi_type_data_chunk] "
                                        f"Index {i} out of bounds for N_epoch.shape[1]={N_epoch.shape[1]}, using last value"
                                    )
                        else:
                            abundance = N_epoch[type_idx]
                        self.buffer_N_by_lineage[idx][lineage_id] = float(abundance)
                    except IndexError as e:
                        if DEBUG_INTERPOLATION:
                            logging.error(
                                f"[AnimationController.add_multi_type_data_chunk] IndexError: "
                                f"type_idx={type_idx}, i={i}, N_epoch.shape={N_epoch.shape}, error={e}"
                            )
                        self.buffer_N_by_lineage[idx][lineage_id] = 0.0

        # DIAGNOSTIC LOGGING (throttled)
        if not hasattr(self, '_multi_type_chunk_count'):
            self._multi_type_chunk_count = 0
        self._multi_type_chunk_count += 1

        if self._multi_type_chunk_count % 20 == 0 or len(t_list) == 1:
            print(f"[AnimCtrl] add_multi_type_data_chunk #{self._multi_type_chunk_count}: "
                  f"N_epoch.shape={N_epoch.shape}, lineageIDs={len(lineageIDs)}, "
                  f"t_points={len(t_list)}, global_lineages={len(self._global_lineage_list)}", flush=True)

        #------------------------------
        # Update integration time
        #------------------------------
        if len(self.buffer_times) > 0:
            self.integration_time = self.buffer_times[-1]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _interpolate_multi_type_abundance(self, t):
        """
        Interpolate all type abundances at a specific time.

        Uses linear interpolation for each type independently to provide
        smooth animation.

        Args:
            t (float): Simulation time to interpolate at

        Returns:
            dict: {lineageID: interpolated_abundance}
        """
        #------------------------------
        # Validate buffer has data
        #------------------------------
        if len(self.buffer_times) == 0 or len(self.buffer_N_by_lineage) == 0:
            return {}

        # Ensure buffer arrays match in length
        if len(self.buffer_times) != len(self.buffer_N_by_lineage):
            if DEBUG_INTERPOLATION:
                logging.warning(
                    f"[AnimationController._interpolate_multi_type_abundance] Buffer length mismatch: "
                    f"times={len(self.buffer_times)}, N_by_lineage={len(self.buffer_N_by_lineage)}"
                )
            # Use minimum length
            min_len = min(len(self.buffer_times), len(self.buffer_N_by_lineage))
            self.buffer_times = self.buffer_times[:min_len]
            self.buffer_biomass = self.buffer_biomass[:min_len]
            self.buffer_N_by_lineage = self.buffer_N_by_lineage[:min_len]

        #------------------------------
        # Handle edge cases
        #------------------------------
        if t <= self.buffer_times[0]:
            return self.buffer_N_by_lineage[0].copy()

        if t >= self.buffer_times[-1]:
            return self.buffer_N_by_lineage[-1].copy()

        #------------------------------
        # Find bracketing indices for interpolation
        #------------------------------
        idx = bisect_left(self.buffer_times, t)

        t0, t1 = self.buffer_times[idx-1], self.buffer_times[idx]
        N_dict0 = self.buffer_N_by_lineage[idx-1]
        N_dict1 = self.buffer_N_by_lineage[idx]

        #------------------------------
        # Interpolate each lineage independently
        #------------------------------
        alpha = (t - t0) / (t1 - t0) if t1 > t0 else 0

        N_interp = {}
        all_lineages = set(N_dict0.keys()) | set(N_dict1.keys())

        for lineage_id in all_lineages:
            y0 = N_dict0.get(lineage_id, 0.0)
            y1 = N_dict1.get(lineage_id, 0.0)
            N_interp[lineage_id] = y0 + alpha * (y1 - y0)

        return N_interp

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_mutation_events_in_range(self, t_start, t_end):
        """
        Get mutation events that occurred within a time range.

        Args:
            t_start (float): Start of time range
            t_end (float): End of time range

        Returns:
            list: Times when mutations occurred in the range
        """
        return [t for t in self.mutation_events if t_start <= t <= t_end]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def reset(self):
        """Reset controller to initial state (for new simulation)."""
        self.buffer_times = []
        self.buffer_biomass = []
        self.buffer_N_by_lineage = []
        self.current_lineageIDs = []
        self.mutation_events = []
        self.animation_time = 0.0
        self.integration_time = 0.0
        self.is_playing = True
        self.last_real_time = None

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
