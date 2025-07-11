# controllers/dp5_controller.py
# Controller class for DP5 device logic

import os
import ctypes
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

# Import base class, API module, and Worker
from .base_controller import BaseController
try:
    from api import dp5_api
except ImportError: dp5_api = None; print("ERROR: Could not import api.dp5_api")
except OSError as e: dp5_api = None; print(f"Error loading DP5 API DLL: {e}")
try:
    from workers.dp5_worker import DP5AcquisitionWorker
except ImportError: DP5AcquisitionWorker = None; print("ERROR: Could not import workers.dp5_worker")

class DP5Controller(BaseController):
    acquisition_state_changed = pyqtSignal(bool)
    status_updated = pyqtSignal(object)
    spectrum_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(api_module=dp5_api, parent=parent)
        self._is_acquiring = False
        self._last_config_file = None
        self._worker = None
        self._thread = None
        self._last_spectrum_data = None # Store the last received NumPy array
        self._last_status_data = None   # Store the last received status ctypes structure

    # --- Properties ---
    @property
    def is_acquiring(self): return self._is_acquiring
    @property
    def last_config_file(self): return self._last_config_file

    # --- Public Control Methods ---
    def connect(self):
        if not self._api: return self._report_error("DP5 API not loaded.")
        if self.is_connected: return self._post_status_message("DP5 already connected.")
        if self._is_acquiring: return self._report_error("Cannot connect while acquiring.")
        self._post_status_message("Connecting to DP5 via USB...")
        try:
            try: self._api.CloseConnection()
            except Exception: pass
            result = self._api.ConnectToDefaultDPP()
            if result == 1:
                self._set_connected(True); self._post_status_message("DP5 Connected.")
                self.request_single_status_update() # Gets initial status
            else: self._set_connected(False); self._report_error("Failed to connect.")
        except Exception as e: self._set_connected(False); self._report_error(f"DP5 connection error: {e}")

    def disconnect(self):
        if not self._api: return
        if self._is_acquiring:
            print("DP5 Acq running, stopping before disconnect...")
            self.stop_acquisition()
            if self._thread and self._thread.isRunning():
                 if not self._thread.wait(500): print("Warning: DP5 thread did not finish quickly.")
        if not self.is_connected:
            if self._is_acquiring: self._set_acquiring(False)
            return
        self._post_status_message("Disconnecting from DP5...")
        try:
            self._api.CloseConnection()
            self._set_connected(False)
            self._post_status_message("DP5 Disconnected.")
            self._last_spectrum_data = None
            self._last_status_data = None
        except Exception as e:
            self._report_error(f"DP5 disconnection error: {e}")
            self._set_connected(False); self._set_acquiring(False); # Force state
            self._last_spectrum_data = None; self._last_status_data = None # Clear cache on error too

    def load_config(self, filepath: str):
        if not self._api: return self._report_error("DP5 API not loaded.")
        if not self.is_connected: return self._report_error("Connect DP5 first.")
        if self._is_acquiring: return self._report_error("Stop acq first.")
        if not filepath or not os.path.exists(filepath): return self._report_error(f"Bad cfg path: {filepath}")
        self._post_status_message(f"Loading DP5 config: {os.path.basename(filepath)}...")
        try:
            result = self._api.SendConfigFileToDpp(filepath.encode('ascii'))
            if result == 1:
                self._last_config_file = filepath; self._post_status_message("DP5 Config loaded.")
                self.request_single_status_update()
            else: self._report_error("Failed to send DP5 config (API Error).")
        except Exception as e: self._report_error(f"Error loading DP5 config: {e}")

    def start_acquisition(self, preset_time: float = None):
        if not self._api: return self._report_error("DP5 API not loaded.")
        if not DP5AcquisitionWorker: return self._report_error("DP5 Worker class not found.")
        if not self.is_connected: return self._report_error("Connect DP5 first.")
        if self._is_acquiring: return self._post_status_message("DP5 acq already running.")
        if self._thread and self._thread.isRunning():
            print("Warn: Previous acq thread running. Stopping."); self.stop_acquisition()
            if not self._thread.wait(1000): print("Error: Prev thread stop failed."); self._clear_thread_worker_refs(); return self._report_error("Could not stop previous thread.")
        elif self._thread or self._worker: self._clear_thread_worker_refs()
        self._post_status_message("Starting DP5 acquisition...")
        if preset_time and preset_time > 0: self._post_status_message(f"Preset Time: {preset_time:.1f} s")
        self._set_acquiring(True)
        try:
            self._thread = QThread(self)
            self._worker = DP5AcquisitionWorker(config_file_path=self._last_config_file, preset_time=preset_time) # <<< Pass preset_time
            self._worker.moveToThread(self._thread)
            # Connect signals (as before)
            self._worker.status_ready.connect(self._handle_worker_status)
            self._worker.spectrum_ready.connect(self._handle_worker_spectrum)
            self._worker.message.connect(self._handle_worker_message)
            self._worker.error.connect(self._handle_worker_error)
            self._worker.finished.connect(self._handle_worker_finished)
            self._thread.started.connect(self._worker.run)
            self._thread.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._thread.deleteLater)
            self._thread.finished.connect(self._clear_thread_worker_refs)
            print("Starting DP5 acquisition thread object..."); self._thread.start()
        except Exception as e: self._report_error(f"Failed start DP5 acq thread: {e}"); self._set_acquiring(False); self._clear_thread_worker_refs()

    def stop_acquisition(self):
        if not self._is_acquiring: return
        self._post_status_message("Requesting DP5 acquisition stop...")
        if self._worker: self._worker.stop()
        else: print("Warn: Stop requested, worker not found."); self._handle_worker_finished()

    def clear_data(self):
        if not self._api: return self._report_error("DP5 API not loaded.")
        if not self.is_connected: return self._report_error("Connect DP5 first.")
        if self._is_acquiring: return self._report_error("Stop acquisition before clearing data.")
        self._post_status_message("Clearing DP5 data buffer...")
        try:
            self._api.ClearData()
            self._post_status_message("DP5 data buffer cleared.")
            self._last_spectrum_data = None
            self.request_single_status_update() # Update status (counts should be 0)
            if dp5_api: self.spectrum_updated.emit(np.zeros(dp5_api.MAX_BUFFER_DATA, dtype=np.int32))
        except Exception as e: self._report_error(f"Error clearing DP5 data: {e}")

    def save_last_spectrum(self, filepath: str, description: str = "DP5 Spectrum", tag: str = "PYXRF"):
        """Saves the last acquired spectrum to an MCA file."""
        if not self._api or not hasattr(self._api, 'SaveMCADataToFile') or self._api.SaveMCADataToFile is None:
             return self._report_error("Spectrum saving function (SaveMCADataToFile) not available in API.")
        if self._last_spectrum_data is None:
             return self._report_error("No spectrum data acquired or cached yet to save.")

        self._post_status_message(f"Saving spectrum to {os.path.basename(filepath)}...")
        try:
            # 1. Create and Populate Spec structure
            spec_struct = self._api.Spec()
            num_channels = len(self._last_spectrum_data)
            if num_channels > self._api.MAX_BUFFER_DATA:
                return self._report_error(f"Spectrum data length ({num_channels}) exceeds max buffer size ({self._api.MAX_BUFFER_DATA}).")

            spec_struct.CHANNELS = ctypes.c_short(num_channels)
            # --- Copy NumPy data to ctypes array ---
            # Get the underlying ctypes array type defined within the structure
            data_array_type = ctypes.c_long * self._api.MAX_BUFFER_DATA
            # Cast the structure's buffer to the correct array pointer type
            data_ptr = ctypes.cast(spec_struct.DATA, ctypes.POINTER(data_array_type))
            # Ensure source data is the correct type (int32 matches c_long on 32-bit)
            data_to_copy = self._last_spectrum_data.astype(np.int32)
            # Copy data using slicing
            ctypes.memmove(data_ptr.contents, # Destination buffer
                           data_to_copy.ctypes.data, # Source buffer address
                           data_to_copy.nbytes) # Number of bytes to copy
            # --- End Copy ---

            # 2. Create and Populate SpecFile structure
            spec_file_info = self._api.SpecFile()
            # Populate basic fields (truncate and encode)
            max_tag = self._api.MAX_TAG_SIZE - 1
            max_desc = self._api.MAX_DESCRIPTION_SIZE - 1
            spec_file_info.strTag = tag.encode('ascii')[:max_tag]
            spec_file_info.strDescription = description.encode('ascii')[:max_desc]

            # Populate from cached status data if available
            if self._last_status_data:
                spec_file_info.AccumulationTime = ctypes.c_double(self._last_status_data.AccumulationTime)
                spec_file_info.RealTime = ctypes.c_double(self._last_status_data.RealTime)
                spec_file_info.SerialNumber = ctypes.c_ulong(self._last_status_data.SerialNumber)
            # Note: Config, Status, StartTime strings remain empty unless helper functions are added/used

            # 3. Call the API function
            filepath_bytes = filepath.encode('ascii')
            self._api.SaveMCADataToFile(filepath_bytes, ctypes.byref(spec_struct), ctypes.byref(spec_file_info))

            self._post_status_message(f"Spectrum saved: {os.path.basename(filepath)}")
            return True # Indicate success

        except OverflowError as oe:
            self._report_error(f"Error populating file info (string too long?): {oe}")
            return False
        except Exception as e:
            self._report_error(f"Error saving spectrum file '{filepath}': {e}")
            return False

    # --- Internal Slots / Methods ---
    def _set_acquiring(self, acquiring_state: bool):
        if self._is_acquiring != acquiring_state:
            self._is_acquiring = acquiring_state; print(f"DP5Controller: Acq state -> {self._is_acquiring}")
            self.acquisition_state_changed.emit(self._is_acquiring)

    # Modify slots to cache data
    def _handle_worker_status(self, status_struct):
        """Stores status data and re-emits signal."""
        self._last_status_data = status_struct # Cache the ctypes struct
        self.status_updated.emit(status_struct)

    def _handle_worker_spectrum(self, spectrum_array):
        """Stores spectrum data and re-emits signal."""
        self._last_spectrum_data = spectrum_array # Cache the numpy array
        self.spectrum_updated.emit(spectrum_array)

    def _handle_worker_message(self, message):
        self._post_status_message(f"DP5 Worker: {message}")

    def _handle_worker_error(self, message):
        self._report_error(f"DP5 Worker Error: {message}"); self._set_acquiring(False)

    def _handle_worker_finished(self):
        print("DP5 worker finished signal received by controller."); self._set_acquiring(False)

    def _clear_thread_worker_refs(self):
         if hasattr(self, '_worker') and self._worker: print("Clearing DP5 worker ref."); self._worker = None
         if hasattr(self, '_thread') and self._thread: print("Clearing DP5 thread ref."); self._thread = None

    def request_single_status_update(self):
         if not self.is_connected or not self._api or self._is_acquiring: return
         try:
              self._api.GetDppStatus()
              status_struct = self._api.DP5_DP4_FORMAT_STATUS()
              self._api.DppStatusToStruct(ctypes.byref(status_struct))
              self._last_status_data = status_struct # Cache it
              self.status_updated.emit(status_struct)
         except Exception as e: self._report_error(f"Error request single status: {e}")