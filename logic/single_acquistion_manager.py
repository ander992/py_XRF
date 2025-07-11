# logic/single_acquisition_manager.py
# Handles a single DP5 acquisition and save workflow.

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import time
import os

class SingleAcquisitionManager(QObject):
    # Signals for UI feedback
    acquisition_started = pyqtSignal()
    acquisition_finished = pyqtSignal(bool) # True if successful (including save), False otherwise
    acquisition_aborted = pyqtSignal(str)   # Error message if aborted or critical failure
    status_update = pyqtSignal(str)       # For status bar updates

    def __init__(self, dp5_controller, parent=None):
        super().__init__(parent)
        self.dp5_ctrl = dp5_controller

        self._running = False
        self._error_reason = ""
        self._duration = 0.0
        self._save_filepath = ""
        self._spectrum_saved_successfully = False

        if self.dp5_ctrl:
            self.dp5_ctrl.acquisition_state_changed.connect(self._handle_dp5_acq_state_change)
        else:
            print("ERROR: SingleAcquisitionManager created without DP5 controller!")
            self._error_reason = "DP5 controller not provided."

    @property
    def is_running(self):
        """Returns True if an acquisition is currently active."""
        return self._running

    def start_acquisition_and_save(self, duration: float, save_filepath: str):
        """
        Starts a single DP5 acquisition and saves the spectrum to the specified filepath.

        Args:
            duration (float): The acquisition duration in seconds.
            save_filepath (str): The full path where the spectrum file should be saved.

        Returns:
            bool: True if the acquisition process was initiated, False otherwise.
        """
        if self._running:
            self.status_update.emit("Acquisition already in progress.")
            return False

        # --- Validate Inputs & States ---
        error = None
        if not self.dp5_ctrl:
            error = "DP5 controller is missing."
        elif not self.dp5_ctrl.is_connected:
            error = "DP5 not connected."
        elif self.dp5_ctrl.is_acquiring:
            error = "DP5 is already acquiring."
        elif not isinstance(duration, (int, float)) or duration <= 0:
            error = f"Invalid duration value: {duration}"
        elif not save_filepath:
            error = "Invalid save filepath (empty)."
        else:
            save_dir = os.path.dirname(save_filepath)
            if not os.path.isdir(save_dir):
                error = f"Save directory does not exist: {save_dir}"

        if error:
            print(f"Single Acquisition Start Error: {error}")
            self.status_update.emit(f"Acquisition Error: {error}")
            # Do not emit acquisition_aborted here, as it's for active sequences
            return False

        self._running = True
        self._error_reason = ""
        self._spectrum_saved_successfully = False
        self._duration = duration
        self._save_filepath = save_filepath

        print(f"SingleAcquisitionManager: Starting acquisition (Duration: {self._duration}s, Save to: {self._save_filepath})")
        self.status_update.emit(f"Starting acquisition ({self._duration}s)...")
        self.acquisition_started.emit()

        try:
            if not self.dp5_ctrl: # Should be caught by initial check, but defensive
                 raise RuntimeError("DP5 Controller missing at point of acquisition start.")
            self.dp5_ctrl.start_acquisition(preset_time=self._duration)
            # Now we wait for _handle_dp5_acq_state_change when acquiring becomes False
            return True
        except Exception as e:
            self._abort_acquisition(f"Error starting DP5 acquisition: {e}")
            return False

    def stop_acquisition(self, reason="User aborted"):
        """Requests the acquisition to stop prematurely."""
        if self._running:
            print(f"SingleAcquisitionManager: Abort requested. Reason: {reason}")
            self._abort_acquisition(reason)
        else:
            print("SingleAcquisitionManager: Stop requested but acquisition not running.")

    def _handle_dp5_acq_state_change(self, acquiring):
        """Slot connected to dp5_ctrl.acquisition_state_changed."""
        print(f"DEBUG (SingleAcqMgr): _handle_dp5_acq_state_change(acquiring={acquiring}). Running: {self._running}, Error: '{self._error_reason}'")

        # Only act if sequence is running, no error yet, and DP5 just *stopped*
        if self._running and not self._error_reason and not acquiring:
            print(f"SingleAcquisitionManager: Detected DP5 finished acquisition.")
            self.status_update.emit("DP5 acquisition finished. Attempting to save spectrum...")

            save_success = self._save_spectrum()
            self._spectrum_saved_successfully = save_success # Store save outcome

            # Finalize will use _spectrum_saved_successfully and _error_reason
            self._finalize()


    def _save_spectrum(self):
        """Attempts to save the last acquired spectrum."""
        if not self._save_filepath:
            self._error_reason = "Save filepath not set before trying to save."
            self.status_update.emit(f"Save Error: {self._error_reason}")
            print(f"SingleAcquisitionManager: {self._error_reason}")
            return False

        if not self.dp5_ctrl:
            self._error_reason = "DP5 Controller missing for saving."
            self.status_update.emit(f"Save Error: {self._error_reason}")
            print(f"SingleAcquisitionManager: {self._error_reason}")
            return False

        self.status_update.emit(f"Saving spectrum to {os.path.basename(self._save_filepath)}...")
        print(f"SingleAcquisitionManager: Saving spectrum to {self._save_filepath}")
        try:
            description = f"Single acquisition, {self._duration}s, {time.strftime('%Y-%m-%d %H:%M:%S')}"
            save_success = self.dp5_ctrl.save_last_spectrum(filepath=self._save_filepath, description=description, tag="SGLPYXRF")

            if save_success:
                self.status_update.emit(f"Spectrum saved: {os.path.basename(self._save_filepath)}")
                print(f"SingleAcquisitionManager: Spectrum saved successfully.")
                return True
            else:
                self._error_reason = "DP5 controller reported failure saving spectrum."
                self.status_update.emit(f"Save Failed: {self._error_reason}")
                print(f"SingleAcquisitionManager: {self._error_reason}")
                return False
        except Exception as e:
            self._error_reason = f"Exception during spectrum save: {e}"
            self.status_update.emit(f"Save Error: {self._error_reason}")
            print(f"SingleAcquisitionManager: {self._error_reason}")
            return False

    def _finalize(self):
        """Final cleanup step, ensures state reset and signals emission."""
        if not self._running: # Only finalize once
             print("SingleAcquisitionManager: Finalize called but not running or already finalized.")
             return

        print(f"SingleAcquisitionManager: Finalizing acquisition (Error='{self._error_reason}', SavedOK={self._spectrum_saved_successfully}).")
        was_running = self._running
        self._running = False # Set state immediately

        if self._error_reason: # If any error occurred during start, acq, or save
            # acquisition_aborted signal would have been emitted by _abort_acquisition
            # or will be emitted now if error happened after DP5 finished but before/during save
            if was_running: # Avoid double emit if already aborted
                 self.acquisition_aborted.emit(self._error_reason)
                 self.status_update.emit(f"Acquisition FAILED: {self._error_reason}")
            self.acquisition_finished.emit(False) # Signal finished with failure
        elif was_running and self._spectrum_saved_successfully: # Explicitly check save success
            self.status_update.emit("Acquisition and save completed successfully.")
            self.acquisition_finished.emit(True) # Signal finished with success
        elif was_running and not self._spectrum_saved_successfully: # Acq done, but save failed
            # Error reason should be set by _save_spectrum
            self.status_update.emit(f"Acquisition completed, but save FAILED: {self._error_reason if self._error_reason else 'Unknown save error'}")
            self.acquisition_aborted.emit(self._error_reason if self._error_reason else "Spectrum save failed.")
            self.acquisition_finished.emit(False) # Signal finished with failure
        
        # Reset error reason and save status for next potential run
        self._error_reason = ""
        self._spectrum_saved_successfully = False


    def _abort_acquisition(self, reason):
        """Internal method to set error state and trigger finalization if running."""
        if not self._running:
            print(f"SingleAcquisitionManager: Abort requested ('{reason}') but not running.")
            return

        print(f"SingleAcquisitionManager: Aborting acquisition! Reason: {reason}")
        self._error_reason = reason # Set error reason first
        self.status_update.emit(f"Acquisition ABORTED: {reason}")
        self.acquisition_aborted.emit(reason) # Emit abort signal

        # If DP5 is currently acquiring, request it to stop
        if self.dp5_ctrl and self.dp5_ctrl.is_acquiring:
             print("SingleAcquisitionManager: Requesting DP5 stop due to abort...")
             self.dp5_ctrl.stop_acquisition()
             # Finalize will be called by _handle_dp5_acq_state_change when acq stops
             # or immediately if DP5 wasn't actually acquiring.
             # However, to be safe and ensure timely finalization:
             if not self.dp5_ctrl.is_acquiring: # If stop was instant or not needed
                 self._finalize()
        else: # Not acquiring, so finalize directly
            self._finalize()