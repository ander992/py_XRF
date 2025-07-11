# workers/dp5_worker.py
# ADDED: Debug print statements

import os
import time
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

# Import API module safely
try:
    from api import dp5_api # Import the module itself
    import ctypes
    DP5_API_LOADED = True
except ImportError:
    dp5_api = None # Ensure dp5_api exists, even if None
    DP5_API_LOADED = False
    print("ERROR: Could not import api.dp5_api in worker")
except OSError as e:
    dp5_api = None
    DP5_API_LOADED = False
    print(f"Error loading DP5 API DLL in worker: {e}")


class DP5AcquisitionWorker(QObject):
    # (Signals as before)
    status_ready = pyqtSignal(object)
    spectrum_ready = pyqtSignal(object)
    message = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, config_file_path=None, preset_time=None, parent=None):
        super().__init__(parent)
        self._running = False
        self._config_file_path = config_file_path
        self._preset_time = preset_time
        self._spectrum_buffer = None
        self._status_buffer = None

        # Use the flag to check if API loaded successfully before creating structs
        if DP5_API_LOADED and dp5_api:
            try:
                self._spectrum_buffer = dp5_api.Spec()
                self._status_buffer = dp5_api.DP5_DP4_FORMAT_STATUS()
            except AttributeError:
                print("Error: DP5 API module loaded but missing Spec/Status structs.")
                self.error.emit("DP5 API Structs missing.")
            except Exception as e:
                print(f"Error allocating DP5 buffers: {e}")
                self.error.emit(f"Error allocating DP5 buffers: {e}")
        elif not DP5_API_LOADED:
             print("DP5 Worker Init: DP5 API not loaded.")


    def run(self):
        """Main acquisition loop with timed acquisition support."""
        # --- Initial Checks ---
        if not DP5_API_LOADED or not dp5_api:
            self.error.emit("DP5 API not loaded. Cannot start worker.")
            self.finished.emit()
            return
        if self._spectrum_buffer is None or self._status_buffer is None:
             self.error.emit("DP5 API buffers not allocated. Cannot start worker.")
             self.finished.emit()
             return

        print("DP5 Worker thread started.")
        self._running = True
        acq_started = False
        config_ok = True # Assume okay unless something fails

        try:
            # 1. Send Configuration
            if self._config_file_path:
                self.message.emit(f"Sending config: {os.path.basename(self._config_file_path)}")
                if not os.path.exists(self._config_file_path):
                     self.error.emit(f"Config file not found: {self._config_file_path}")
                     config_ok = False
                else:
                    if not hasattr(dp5_api, 'SendConfigFileToDpp') or dp5_api.SendConfigFileToDpp is None:
                         self.error.emit("SendConfigFileToDpp function not available in API.")
                         config_ok = False
                    else:
                        try:
                            if dp5_api.SendConfigFileToDpp(self._config_file_path.encode('ascii')) == 1:
                                self.message.emit("Config sent."); time.sleep(0.2)
                            else: self.error.emit("Failed send config (API Error)."); config_ok = False
                        except Exception as e: self.error.emit(f"Error sending config: {e}"); config_ok = False
            else:
                self.message.emit("No config file specified."); # config_ok remains True

            # 2. Send PRET command
            if config_ok:
                if not hasattr(dp5_api, 'send_ascii_command') or dp5_api.send_ascii_command is None:
                     self.error.emit("send_ascii_command helper not available in API module.")
                     config_ok = False
                else:
                    try:
                        pret_command = "PRET=OFF;"
                        if self._preset_time is not None and self._preset_time > 0:
                            pret_command = f"PRET={self._preset_time:.1f};"

                        # --- DEBUG PRINT ---
                        print(f"DP5 WORKER: Sending command: {pret_command}")
                        # --- END DEBUG ---
                        self.message.emit(f"Sending Preset Command: {pret_command}")

                        send_success = dp5_api.send_ascii_command(pret_command)
                        # --- DEBUG PRINT ---
                        print(f"DP5 WORKER: send_ascii_command result: {send_success}")
                        # --- END DEBUG ---

                        if not send_success:
                            self.error.emit(f"Failed send command: {pret_command}")
                            if "PRET=OFF" not in pret_command:
                                 config_ok = False
                        else:
                             self.message.emit("Preset command sent.")

                    except Exception as e_pret:
                        self.error.emit(f"Exception sending PRET command: {e_pret}")
                        config_ok = False

            # 3. Enable MCA
            if config_ok:
                 if not hasattr(dp5_api, 'EnableMCA') or dp5_api.EnableMCA is None:
                      self.error.emit("EnableMCA function not available in API.")
                      config_ok = False
                 else:
                    try:
                        self.message.emit("Enabling MCA...")
                        dp5_api.EnableMCA()
                        acq_started = True
                        self.message.emit("Acquisition Running...")
                    except Exception as e:
                        self.error.emit(f"Error enabling MCA: {e}")
                        acq_started = False
            else:
                 self.message.emit("Skipping MCA enable due to previous setup failure.")
                 acq_started = False

            # 4. Acquisition Loop Checks
            status_funcs_ok = (hasattr(dp5_api, 'GetDppStatus') and dp5_api.GetDppStatus and
                               hasattr(dp5_api, 'DppStatusToStruct') and dp5_api.DppStatusToStruct)
            spectrum_func_ok = (hasattr(dp5_api, 'RequestSpectrumData') and dp5_api.RequestSpectrumData)

            if not status_funcs_ok or not spectrum_func_ok:
                 self.error.emit("Required API functions for acquisition loop missing.")
                 acq_started = False

            # --- Acquisition Loop ---
            while self._running and acq_started:
                try:
                    # Fetch Status
                    dp5_api.GetDppStatus()
                    dp5_api.DppStatusToStruct(ctypes.byref(self._status_buffer))
                    status_copy = ctypes.pointer(self._status_buffer).contents
                    self.status_ready.emit(status_copy)

                    # Check MCA Enabled flag
                    mca_enabled_flag = (self._status_buffer.RAW[35] >> 5) & 1
                    # --- DEBUG PRINT ---
                    print(f"DP5 WORKER: Loop running... MCA Flag (RAW[35] bit 5): {mca_enabled_flag}")
                    # --- END DEBUG ---

                    if mca_enabled_flag == 0:
                        # --- DEBUG PRINT ---
                        print("DP5 WORKER: Detected MCA flag is 0!")
                        # --- END DEBUG ---
                        self.message.emit("MCA Disabled flag detected. Acquisition finished.")
                        self._running = False # Signal loop to stop

                        # Request final spectrum
                        try:
                             dp5_api.RequestSpectrumData(ctypes.byref(self._spectrum_buffer), ctypes.byref(self._status_buffer))
                             num_channels = self._spectrum_buffer.CHANNELS
                             if num_channels > 0 and num_channels <= dp5_api.MAX_BUFFER_DATA:
                                 spectrum_np = np.ctypeslib.as_array(self._spectrum_buffer.DATA)[:num_channels].copy()
                                 self.spectrum_ready.emit(spectrum_np)
                        except Exception as e_final:
                             self.error.emit(f"Error getting final spectrum: {e_final}")
                        continue # Stop processing this iteration

                    # Get spectrum if still running
                    dp5_api.RequestSpectrumData(ctypes.byref(self._spectrum_buffer), ctypes.byref(self._status_buffer))
                    num_channels = self._spectrum_buffer.CHANNELS
                    if num_channels > 0 and num_channels <= dp5_api.MAX_BUFFER_DATA:
                        spectrum_np = np.ctypeslib.as_array(self._spectrum_buffer.DATA)[:num_channels].copy()
                        self.spectrum_ready.emit(spectrum_np)

                    time.sleep(0.5) # Polling interval

                except AttributeError as ae:
                     self.error.emit(f"API attribute error during loop: {ae}"); self._running = False; break
                except Exception as loop_e:
                     self.error.emit(f"Error during acquisition loop: {loop_e}")

        except Exception as setup_e:
            self.error.emit(f"DP5 Acquisition setup error: {setup_e}")
            acq_started = False
        finally:
            # 5. Clean up
            if acq_started and DP5_API_LOADED and dp5_api and hasattr(dp5_api, 'DisableMCA') and dp5_api.DisableMCA:
                try:
                    current_mca_enabled = True
                    try:
                         if status_funcs_ok: # Check if status funcs are okay before trying final check
                              dp5_api.GetDppStatus()
                              final_status = dp5_api.DP5_DP4_FORMAT_STATUS()
                              dp5_api.DppStatusToStruct(ctypes.byref(final_status))
                              current_mca_enabled = (final_status.RAW[35] >> 5) & 1
                    except: pass

                    if current_mca_enabled:
                         self.message.emit("Disabling MCA...")
                         dp5_api.DisableMCA()
                         self.message.emit("MCA Disabled.")
                except Exception as e_stop:
                     err_msg = f"Error disabling MCA on exit: {e_stop}"
                     self.error.emit(err_msg); print(err_msg)

            # --- DEBUG PRINT ---
            print("DP5 WORKER: Emitting finished signal.")
            # --- END DEBUG ---
            self.finished.emit()
            self._running = False # Ensure running flag is false

    def stop(self):
        """Sets the flag to stop the acquisition loop."""
        if self._running:
             self.message.emit("Stop requested.")
             print("DP5 Worker stop requested.")
        self._running = False