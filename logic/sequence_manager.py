# logic/sequence_manager.py
# Handles the multi-acquisition sequence workflow

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QEventLoop
import time
import os

class SequenceManager(QObject):
    # Signals for UI feedback
    sequence_started = pyqtSignal()
    sequence_step_starting = pyqtSignal(int, int) # current_rep, total_reps
    sequence_step_finished = pyqtSignal(int, int) # current_rep, total_reps
    sequence_pausing = pyqtSignal(int) # pause_duration_ms
    sequence_finished = pyqtSignal(int) # total_reps_completed
    sequence_aborted = pyqtSignal(str) # error message
    status_update = pyqtSignal(str) # For status bar updates
    request_safe_hv_on = pyqtSignal()

    def __init__(self, minix_controller, dp5_controller, parent=None):
        super().__init__(parent)
        self.minix_ctrl = minix_controller
        self.dp5_ctrl = dp5_controller

        self._running = False
        self._error_reason = ""
        self._current_rep = 0
        self._total_reps = 0
        self._duration = 0.0
        self._minix_continuous = False
        self._save_folder = ""
        self._pause_ms = 5000 # Pause between repetitions

        # Connect to DP5 signal needed to advance sequence
        if self.dp5_ctrl:
            self.dp5_ctrl.acquisition_state_changed.connect(self._handle_dp5_acq_state_change)
        else:
            print("WARNING: SequenceManager created without DP5 controller!")

    @property
    def is_running(self):
        """Returns True if a sequence is currently active."""
        return self._running

    def start_sequence(self, repetitions, duration, minix_continuous, save_folder):
        """
        Starts the acquisition sequence after validating parameters and device states.
        Returns True if sequence start was initiated, False otherwise.
        """
        if self._running:
            self.status_update.emit("Sequence already running.")
            return False

        # --- Validate Inputs & States ---

        error = None
        if not self.minix_ctrl or not self.minix_ctrl.is_connected:
            error = "MiniX not connected."
        elif not self.dp5_ctrl or not self.dp5_ctrl.is_connected:
            error = "DP5 not connected."
        elif self.dp5_ctrl.is_acquiring: # Check DP5 isn't already busy
            error = "DP5 is already acquiring."
        elif not isinstance(repetitions, int) or repetitions <= 0:
            error = f"Invalid repetitions value: {repetitions}"
        elif not isinstance(duration, (int, float)) or duration <= 0:
            error = f"Invalid duration value: {duration}"
        elif not save_folder or not os.path.isdir(save_folder):
            error = f"Invalid or non-existent save folder: {save_folder}"

        if error:
             print(f"Sequence Start Error: {error}")
             self.status_update.emit(f"Sequence Error: {error}")
             self.sequence_aborted.emit(error)

        self._running = True
        self._error_reason = ""
        self._current_rep = 0
        self._total_reps = repetitions
        self._duration = duration
        self._minix_continuous = minix_continuous
        self._save_folder = save_folder

        print("Sequence Manager: Starting sequence...")
        self.status_update.emit(f"Starting sequence: {self._total_reps} reps...")
        self.sequence_started.emit() # Signal UI to update state

        # --- Initial HV On (Continuous Mode) ---
        if self._minix_continuous:
            print("Sequence Manager: Turning HV ON (Continuous)")
            # Signal main window to handle the safe HV ON request
            self.request_safe_hv_on.emit()
            # We cannot directly confirm success here easily without more signals
            # Assume it worked or rely on later checks/errors
            self._wait_with_events(1000) # Allow time for HV ON attempt/stabilization

        # --- Start First Step ---
        # Use a timer to slightly delay the first step, allowing UI updates
        QTimer.singleShot(50, self._run_next_step)
        return True

    def stop_sequence(self, reason="User aborted"):
        """Requests the sequence to stop prematurely."""
        if self._running:
            print(f"Sequence Manager: Abort requested. Reason: {reason}")
            self._abort_sequence(reason)
        else:
            print("Sequence Manager: Stop requested but sequence not running.")

    # --- Internal Sequence Logic ---
    def _run_next_step(self):
        print(f"SEQ MGR: Calling dp5_ctrl.start_acquisition with preset_time={self._duration}")
        """Executes the next acquisition step or finalizes if done/error."""
        if not self._running:
            print("Sequence Manager: _run_next_step called but sequence not running.")
            self._finalize() # Ensure final state if called unexpectedly
            return
        if self._error_reason:
            print(f"Sequence Manager: _run_next_step called but error occurred ('{self._error_reason}').")
            self._finalize()
            return

        self._current_rep += 1
        if self._current_rep > self._total_reps:
            print("Sequence Manager: All repetitions completed.")
            self._finalize()
            return

        # --- Prepare for Current Repetition ---
        print(f"Sequence Manager: --- Starting Rep {self._current_rep}/{self._total_reps} ---")
        self.status_update.emit(f"Running Rep {self._current_rep}/{self._total_reps} ({self._duration}s)...")
        self.sequence_step_starting.emit(self._current_rep, self._total_reps)

        try:
            # --- HV Control (Non-Continuous) ---
            if not self._minix_continuous:
                print(f"Sequence Manager: Turning HV ON for Rep {self._current_rep}")
                # Signal main window for safe HV ON
                self.request_safe_hv_on.emit()
                # How to check success/wait? Rely on timing for now.
                self._wait_with_events(500) # Allow time for HV ON

            # --- Start DP5 Acquisition ---
            print(f"Sequence Manager: Starting DP5 for Rep {self._current_rep}")
            if self.dp5_ctrl:
                # Check if DP5 is still connected before starting
                if not self.dp5_ctrl.is_connected:
                     raise RuntimeError("DP5 disconnected before starting repetition.")
                self.dp5_ctrl.start_acquisition(preset_time=self._duration)
                # Now wait for _handle_dp5_acq_state_change when acquiring becomes False
            else:
                raise RuntimeError("DP5 Controller missing.")

        except Exception as e:
             self._abort_sequence(f"Error starting Rep {self._current_rep}: {e}")

    def _handle_dp5_acq_state_change(self, acquiring):
        """Slot connected to dp5_ctrl.acquisition_state_changed."""
        print(f"DEBUG: _handle_dp5_acq_state_change called with acquiring={acquiring}. Sequence running: {self._running}, Error: '{self._error_reason}'")

        # Only act if sequence is running, no error yet, and DP5 just *stopped*
        if self._running and not self._error_reason and not acquiring:
            print(f"Sequence Manager: Detected DP5 finished Rep {self._current_rep}")
            self.sequence_step_finished.emit(self._current_rep, self._total_reps)

            # --- Spectrum Saving Logic ---
            save_success = False
            try:
                 if not self._save_folder or not os.path.isdir(self._save_folder):
                      raise IOError(f"Save folder disappeared or invalid: {self._save_folder}")

                 timestamp = time.strftime("%Y%m%d_%H%M%S")
                 # Define filename HERE
                 filename = os.path.join(self._save_folder, f"spectrum_rep{self._current_rep:03d}_{timestamp}.mca")

                 # --- DEBUG PRINT (Moved Here) ---
                 print(f"SEQ MGR: Attempting to save file: {filename}")
                 # --- END DEBUG ---

                 self.status_update.emit(f"Saving Rep {self._current_rep} spectrum...")
                 print(f"Sequence Manager: Saving spectrum for Rep {self._current_rep} to {filename}")

                 if not self.dp5_ctrl:
                     raise RuntimeError("DP5 Controller missing for saving.")

                 save_success = self.dp5_ctrl.save_last_spectrum(filepath=filename, description=f"Rep {self._current_rep}/{self._total_reps}", tag="SEQPYXRF")
                 print(f"SEQ MGR: Save result: {save_success}") # DEBUG

                 if not save_success:
                      raise RuntimeError(f"DP5 controller reported failure saving spectrum.")
                 else:
                      self.status_update.emit(f"Rep {self._current_rep} spectrum saved.")

            except Exception as e:
                 self._abort_sequence(f"Error saving spectrum for Rep {self._current_rep}: {e}")
                 return # Stop processing this step
            # --- End Spectrum Saving Logic ---

            # --- HV Control (Non-Continuous) ---
            if not self._minix_continuous:
                 print(f"Sequence Manager: Turning HV OFF for Rep {self._current_rep}")
                 if self.minix_ctrl: self.minix_ctrl.set_hv_off()
                 self._wait_with_events(100)

            # --- Pause or Proceed ---
            if self._current_rep < self._total_reps:
                 print(f"Sequence Manager: Pausing after Rep {self._current_rep} for {self._pause_ms}ms")
                 self.status_update.emit(f"Rep {self._current_rep} finished. Pausing...")
                 self.sequence_pausing.emit(self._pause_ms)
                 QTimer.singleShot(self._pause_ms, self._run_next_step)
            else:
                 print("Sequence Manager: Last repetition finished.")
                 QTimer.singleShot(10, self._run_next_step)

    def _finalize(self):
        """Final cleanup step, ensures state reset and signals emission."""
        if not self._running and not self._error_reason: # Only finalize once properly
             print("Sequence Manager: Finalize called but already finalized/stopped.")
             return

        print(f"Sequence Manager: Finalizing sequence (Error='{self._error_reason}').")
        was_running = self._running
        self._running = False # Set state immediately

        # --- Final HV Off (Continuous Mode) ---
        # Ensure HV is turned off if continuous mode was used and sequence was running
        if self._minix_continuous and was_running:
            print("Sequence Manager: Turning HV OFF (Continuous Mode)")
            if self.minix_ctrl:
                try: self.minix_ctrl.set_hv_off()
                except Exception as e: print(f"Sequence Manager: Error turning HV off: {e}")

        # --- Emit Final Signal ---
        if self._error_reason:
            # Aborted signal already emitted in _abort_sequence
             pass
        elif was_running: # Only emit 'finished' if it was running and not aborted
            final_reps = self._current_rep -1 if self._current_rep > self._total_reps else self._current_rep # Correct count if finalize called after last step
            self.status_update.emit(f"Sequence finished ({final_reps}/{self._total_reps} repetitions).")
            self.sequence_finished.emit(final_reps)

        # Reset error reason for next potential run
        self._error_reason = ""


    def _abort_sequence(self, reason):
        """Internal method to set error state and trigger finalization."""
        if not self._running: return
        print(f"Sequence Manager: Aborting sequence! Reason: {reason}")
        self._error_reason = reason
        self.status_update.emit(f"Sequence ABORTED: {reason}")
        self.sequence_aborted.emit(reason)

        # If DP5 is currently acquiring, request it to stop
        if self.dp5_ctrl and self.dp5_ctrl.is_acquiring:
             print("Sequence Manager: Requesting DP5 stop due to abort...")
             self.dp5_ctrl.stop_acquisition()
             # Finalize will handle HV off etc. after DP5 stops
        self._finalize()


    def _wait_with_events(self, duration_ms):
        """Pauses execution for a duration while keeping the UI responsive."""
        if duration_ms <= 0: return
        loop = QEventLoop()
        QTimer.singleShot(duration_ms, loop.quit)
        loop.exec_()