# Controller class for Mini-X device logic

import sys
import time
from PyQt5.QtCore import pyqtSignal, QTimer
from .base_controller import BaseController

try:
    from api import minix_api
except ImportError:
    print("ERROR: Could not import api.minix_api in minix_controller.py"); sys.exit(1)

class MiniXController(BaseController):
    """
    Controller for managing interaction with the Amptek Mini-X device.
    Handles state, API calls, status polling, and emits signals for UI updates.
    """

    # --- Mini-X Specific Signals ---
    # Emitted when the background controller app starts or stops
    controller_running_changed = pyqtSignal(bool)
    # Emitted periodically with the latest monitor data structure
    monitor_data_updated = pyqtSignal(object)
    # Emitted when HV state actually changes (based on monitor data)
    hv_state_changed = pyqtSignal(bool)
    # Emitted when HV/Current settings are read back (optional)
    # settings_data_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        """Initialize the MiniXController."""
        # Pass the specific API module to the base class
        super().__init__(api_module=minix_api, parent=parent)

        # --- Mini-X Specific State ---
        self._is_controller_app_running = False
        self._hv_on = False # Tracks HV state based on last monitor update
        self._monitor_data = None # Store last received monitor data struct

        # --- Timer for Status Polling ---
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._poll_status)
        self._monitor_interval_ms = 1000 # Default polling interval

        # --- Initial Check for Running Controller ---
        self._check_initial_controller_state()

    # --- Properties ---
    @property
    def is_controller_app_running(self):
        """Is the background controller application process running?"""
        return self._is_controller_app_running

    @property
    def hv_on(self):
        """Is the high voltage currently on (based on last status poll)?"""
        return self._hv_on

    @property
    def last_monitor_data(self):
        """Return the last received monitor data structure."""
        return self._monitor_data

    # --- Public Control Methods ---
    def start_controller_app(self):
        """Starts the background Mini-X controller process."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        if self._is_controller_app_running: return self._post_status_message("Controller app already running.")

        self._post_status_message("Starting Mini-X Controller Application...")
        try:
            self._api.start_controller_application()
            # Verify it started (is_controller_running might take a moment)
            time.sleep(0.5) # Small delay to allow startup
            if self._api.is_controller_running():
                self._set_controller_running(True)
                self._post_status_message("Controller Application Started.")
                self.start_monitoring() # Start polling status
            else:
                 # It might have failed immediately or is slow starting
                 # Keep state as not running for now, polling might catch it later
                 self._set_controller_running(False)
                 self._report_error("Controller application failed to start or is slow responding.")

        except self._api.ControllerNotRunningError as e: # Should not happen here but catch anyway
             self._set_controller_running(False)
             self._report_error(f"Controller start failed: {e}")
        except Exception as e:
            self._set_controller_running(False)
            self._report_error(f"Unexpected error starting controller: {e}")

    def close_controller_app(self):
        """Closes the background Mini-X controller process."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        if not self._is_controller_app_running: return self._post_status_message("Controller app not running.")

        self._post_status_message("Closing Mini-X Controller Application...")
        self.stop_monitoring()
        try:
            # Attempt graceful hardware disconnect first if connected
            if self.is_connected:
                try:
                    print("Sending mxcExit before closing controller app...")
                    # Use False for check_enabled as we want to send regardless of exact state
                    self._api.send_command(self._api.MiniXCommands.mxcExit, check_enabled=False)
                    time.sleep(0.5) # Give command time
                except Exception as e_exit:
                    # Log but continue trying to close the app
                    print(f"Ignoring error sending mxcExit: {e_exit}")

            self._api.close_controller_application()
            self._set_controller_running(False) # Update state first
            self._set_connected(False) # Closing controller implies disconnect
            self._set_hv_on(False) # HV must be off if controller is closed
            self._post_status_message("Controller Application Closed.")
        except Exception as e:
            # State might be uncertain here
            self._report_error(f"Error closing controller application: {e}")
            # Force state update anyway? Or leave as potentially running? Forcing seems safer.
            self._set_controller_running(False)
            self._set_connected(False)
            self._set_hv_on(False)

    def connect_hardware(self):
        """Connects to the Mini-X hardware via the running controller app."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        if not self._is_controller_app_running: return self._report_error("Controller application not running.")
        if self.is_connected: return self._post_status_message("Hardware already connected.")

        self._post_status_message("Attempting to connect to MiniX hardware...")
        try:
            # Check current status from controller
            monitor = self._api.get_monitor_data() # Raises ControllerNotRunningError if it stopped
            current_status_enum = self._api.MiniXStatus(monitor.mxmStatusInd)

            if current_status_enum == self._api.MiniXStatus.mxstMiniXApplicationReady:
                # Send command to connect
                self._api.send_command(self._api.MiniXCommands.mxcStartMiniX, check_enabled=True) # API checks state internally
                # Wait briefly and check status again
                time.sleep(1.5) # Allow connection time
                monitor = self._api.get_monitor_data() # Re-check status
                current_status_enum = self._api.MiniXStatus(monitor.mxmStatusInd)

                if current_status_enum in [self._api.MiniXStatus.mxstMiniXControllerReady, self._api.MiniXStatus.mxstMiniXReady]:
                    self._set_connected(True)
                    self._post_status_message(f"MiniX Hardware Connected. Status: {self._api.get_status_string(monitor.mxmStatusInd)}")
                    # Update internal state based on this first successful poll
                    self._update_internal_state(monitor)
                elif current_status_enum == self._api.MiniXStatus.mxstNoDevicesAttached:
                    self._set_connected(False)
                    self._report_error("MiniX Connection failed: No devices attached or powered.")
                else:
                    self._set_connected(False)
                    self._report_error(f"MiniX Connection failed. Final Status: {self._api.get_status_string(monitor.mxmStatusInd)}")
            elif current_status_enum in [self._api.MiniXStatus.mxstMiniXControllerReady, self._api.MiniXStatus.mxstMiniXReady]:
                 # Already connected according to controller status
                 self._set_connected(True)
                 self._post_status_message(f"MiniX Hardware already connected. Status: {self._api.get_status_string(monitor.mxmStatusInd)}")
                 self._update_internal_state(monitor)
            else:
                 # Controller is running but not in a state ready to connect hardware
                 self._set_connected(False)
                 self._report_error(f"Cannot connect MiniX hardware. Current Status: {self._api.get_status_string(monitor.mxmStatusInd)}")

        except (self._api.ControllerNotRunningError, self._api.APICommandError, self._api.StatusError, TypeError, ValueError) as e:
            self._set_connected(False)
            self._report_error(f"Failed to connect to MiniX hardware: {e}")
        # No finally block needed as state is set within try/except

    def disconnect_hardware(self):
        """Disconnects from the hardware by sending the mxcExit command."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        # Allow sending even if state thinks it's disconnected, controller app manages state
        if not self._is_controller_app_running: return self._report_error("Controller application not running.")

        self._post_status_message("Disconnecting hardware (sending mxcExit)...")
        try:
            # mxcExit should handle hardware disconnect gracefully within controller
            # Use check_enabled=False as the command is valid even if HV is on/off etc.
            self._api.send_command(self._api.MiniXCommands.mxcExit, check_enabled=False)
            # Assume disconnect after sending command - polling will confirm actual state
            self._set_connected(False)
            self._set_hv_on(False) # HV will turn off on disconnect
            self._post_status_message("Hardware disconnect command (mxcExit) sent.")
            # Poll status immediately to get updated state from controller
            self._poll_status()
        except (self._api.ControllerNotRunningError, self._api.APICommandError, TypeError, ValueError) as e:
            self._report_error(f"Could not send disconnect command: {e}")
            # Force internal state update anyway? Assume disconnected if command fails.
            self._set_connected(False)
            self._set_hv_on(False)

    def set_hv_current(self, voltage: float, current: float):
        """Sets the target high voltage (kV) and current (uA)."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        if not self.is_connected: return self._report_error("MiniX not connected.")

        self._post_status_message(f"Setting HV={voltage:.2f}kV, Current={current:.1f}uA...")
        try:
            self._api.set_voltage(voltage)
            # Short delay between commands might be good practice
            time.sleep(0.05)
            self._api.set_current(current)
            time.sleep(0.1) # Allow settings to be processed
            self._post_status_message("Set voltage/current commands sent.")
            # Optionally read back and emit settings confirmation
            # self._fetch_and_emit_settings()
            # Force status poll to see immediate effect if possible
            self._poll_status()
        except (self._api.ControllerNotRunningError, self._api.APICommandError, self._api.StatusError, TypeError, ValueError) as e:
            self._report_error(f"Failed to set voltage/current: {e}")

    def set_hv_on(self):
        """Sends the command to turn High Voltage ON."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        if not self.is_connected: return self._report_error("MiniX not connected.")
        # Safety check should happen in UI layer before calling this method

        self._post_status_message("Attempting to turn HV ON...")
        try:
            self._api.send_command(self._api.MiniXCommands.mxcHVOn, check_enabled=True)
            self._post_status_message("HV ON command sent.")
            # Status update timer will reflect the actual state change
            # Or force immediate poll:
            # time.sleep(0.1)
            # self._poll_status()
        except (self._api.ControllerNotRunningError, self._api.APICommandError, self._api.StatusError, TypeError, ValueError) as e:
            self._report_error(f"Failed to turn HV ON: {e}")

    def set_hv_off(self):
        """Sends the command to turn High Voltage OFF."""
        if not self._api: return self._report_error("MiniX API not loaded.")
        # Allow sending command even if not 'connected' but controller is running,
        # as HV could potentially be stuck on if connection state is wrong.
        # API's check_enabled=True handles internal state check.
        if not self._is_controller_app_running: return self._report_error("Controller not running.")

        self._post_status_message("Attempting to turn HV OFF...")
        try:
            self._api.send_command(self._api.MiniXCommands.mxcHVOff, check_enabled=True)
            self._post_status_message("HV OFF command sent.")
            # Status update timer will reflect the actual state change
            # Or force immediate poll:
            # time.sleep(0.1)
            # self._poll_status()
        except (self._api.ControllerNotRunningError, self._api.APICommandError, self._api.StatusError, TypeError, ValueError) as e:
            self._report_error(f"Failed to turn HV OFF: {e}")

    # --- Monitoring Control ---
    def start_monitoring(self, interval_ms=None):
        """Starts the timer for periodic status updates."""
        if interval_ms is None:
            interval_ms = self._monitor_interval_ms
        else:
            self._monitor_interval_ms = interval_ms # Update default if provided

        if self._monitor_timer.isActive():
            self._monitor_timer.stop()
        self._monitor_timer.start(interval_ms)
        print(f"Started MiniX monitoring timer (interval: {interval_ms}ms).")
        # Perform an immediate update
        self._poll_status()

    def stop_monitoring(self):
        """Stops the status update timer."""
        if self._monitor_timer.isActive():
            self._monitor_timer.stop()
            print("Stopped MiniX monitoring timer.")

    # --- Private Methods ---
    def _check_initial_controller_state(self):
        """Checks if the controller app is running when the controller starts."""
        if self._api and hasattr(self._api, 'is_controller_running'):
            try:
                 if self._api.is_controller_running():
                      self._set_controller_running(True)
                      print("MiniX controller was already running.")
                      self.start_monitoring() # Start polling if already running
                 else:
                      self._set_controller_running(False)
            except Exception as e:
                 print(f"Error during initial check for MiniX controller: {e}")
                 self._set_controller_running(False)
        else:
             self._set_controller_running(False) # API not loaded

    def _set_controller_running(self, running_state: bool):
        """Protected method to update controller running state and emit signal."""
        if self._is_controller_app_running != running_state:
            self._is_controller_app_running = running_state
            self.controller_running_changed.emit(self._is_controller_app_running)
            # If controller stops, it cannot be connected, HV must be off
            if not running_state:
                self._set_connected(False)
                self._set_hv_on(False)
                self.stop_monitoring() # Stop polling if controller stops

    def _set_hv_on(self, hv_state: bool):
        """Protected method to update HV ON state and emit signal."""
        # Ensure hv_state is boolean
        current_hv_state = bool(hv_state)
        if self._hv_on != current_hv_state:
            self._hv_on = current_hv_state
            self.hv_state_changed.emit(self._hv_on)

    def _update_internal_state(self, monitor_data):
         """Updates internal state flags based on received monitor data."""
         if not self._api: return

         # Update internal monitor data cache
         self._monitor_data = monitor_data

         # Infer connection state
         try: # Add try block in case monitor_data is invalid
             current_status_enum = self._api.MiniXStatus(monitor_data.mxmStatusInd)
             new_connected_state = current_status_enum in [self._api.MiniXStatus.mxstMiniXControllerReady,
                                                            self._api.MiniXStatus.mxstMiniXReady]
             self._set_connected(new_connected_state) # Base method handles signal emit

             # Update HV state
             new_hv_state = bool(monitor_data.mxmHVOn)
             self._set_hv_on(new_hv_state) # This method emits hv_state_changed

         except (AttributeError, ValueError, TypeError) as e:
              print(f"Error interpreting monitor data: {e}")
              # Consider reporting error or resetting state if data is bad
              self._report_error("Received invalid monitor data.")
              self._set_connected(False)
              self._set_hv_on(False)

    def _poll_status(self):
        """Polls the device status using get_monitor_data."""
        if not self._api or not self._is_controller_app_running:
            # This case should ideally be caught by _set_controller_running stopping the timer
            # but double-check here.
            if self._monitor_timer.isActive():
                 print("Polling attempted but controller marked as not running. Stopping timer.")
                 self.stop_monitoring()
                 # Ensure state reflects controller stopped
                 self._set_controller_running(False)
            return

        try:
            monitor_data = self._api.get_monitor_data()
            # Update internal state variables (like _is_connected, _hv_on)
            # This also emits connection_changed and hv_state_changed if they changed
            self._update_internal_state(monitor_data)
            # Emit the raw monitor data for the UI
            self.monitor_data_updated.emit(monitor_data)

        except self._api.ControllerNotRunningError:
            self._report_error("Controller application stopped responding.")
            # Update state and stop polling
            self._set_controller_running(False)
            # _set_controller_running already calls stop_monitoring and updates connected/hv state
        except self._api.StatusError as e:
            # Device reported an error state
            self._report_error(f"Device Error: {e}")
            # What should happen? Keep polling? Stop? Assume disconnected?
            # For now, report error and assume disconnected state is safer
            self._set_connected(False)
            self._set_hv_on(False)
            # Optionally stop polling on critical errors?
            # self.stop_monitoring()
        except Exception as e:
            # Generic error during polling
            self._report_error(f"Error during status polling: {e}")
            # Decide whether to stop monitoring on generic errors
            # self.stop_monitoring()

    # --- Optional: Method to fetch current settings ---
    # def _fetch_and_emit_settings(self):
    #     """Fetches current HV/Current settings and emits them."""
    #     if not self._api or not self.is_connected: return
    #     try:
    #         settings = self._api.get_current_settings()
    #         self._settings_data = settings # Cache if needed
    #         # Check if signal exists before emitting
    #         if hasattr(self, 'settings_data_updated'):
    #              self.settings_data_updated.emit(settings)
    #     except Exception as e:
    #         self._report_error(f"Failed to get current settings: {e}")