# py_xrf/ui/acquisition_tab_widget.py
import sys
import numpy as np
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout # Import necessary Qt classes
# Import the generated UI class
try: from .acquisition_ui import Ui_AcquisitionTab
except ImportError: Ui_AcquisitionTab = None; print("Warning: ui.acquisition_ui not found.")

# Import plotting library (optional check)
try: import pyqtgraph as pg
except ImportError: pg = None

# Import API for status string function (optional, could be passed)
try: from api import minix_api
except ImportError: minix_api = None

class AcquisitionTabWidget(QWidget):
    single_acquisition_start_requested = pyqtSignal() # For sequence start
    single_acquisition_stop_requested = pyqtSignal()  # For sequence stop / single acq stop
    single_shot_acquisition_requested = pyqtSignal() # New: For the SINGLE button

    def __init__(self, minix_controller, dp5_controller, parent=None):
        super().__init__(parent)

        # Store controller references
        self.minix_ctrl = minix_controller
        self.dp5_ctrl = dp5_controller

        # Setup the UI defined in Ui_AcquisitionTab
        if Ui_AcquisitionTab:
            self.ui = Ui_AcquisitionTab()
            self.ui.setupUi(self)
            self._connect_signals()
            self.clear_minix_display() # Initialize display
            self.clear_dp5_display()   # Initialize display
            self.clear_plot()          # Initialize display
        else:
            # Fallback if UI class failed to import
            error_layout = QVBoxLayout(self)
            error_layout.addWidget(QLabel("Error: AcquisitionTab UI definition failed to load."))
            self.ui = None # Ensure ui attribute exists but is None

    def _connect_signals(self):
        """Connect signals from UI elements to emit signals or call internal methods."""
        if not self.ui: return
        print("ACQ_TAB: Connecting signals...")

        # --- Connect Acquisition Control Buttons to emit signals ---
        if hasattr(self.ui, 'start_acq_button'): # This is the "Start Sequence" button
            self.ui.start_acq_button.clicked.connect(self.single_acquisition_start_requested)
            print("ACQ_TAB: Connected start_acq_button (Start Sequence) -> single_acquisition_start_requested")
        else: print("ACQ_TAB: Warning - start_acq_button not found in UI.")

        if hasattr(self.ui, 'stop_acq_button'): # This is the "Stop Sequence/Acq" button
            self.ui.stop_acq_button.clicked.connect(self.single_acquisition_stop_requested)
            print("ACQ_TAB: Connected stop_acq_button (Stop Sequence/Acq) -> single_acquisition_stop_requested")
        else: print("ACQ_TAB: Warning - stop_acq_button not found in UI.")

        # --- Connect new SINGLE button ---
        if hasattr(self.ui, 'single_acq_button'):
            self.ui.single_acq_button.clicked.connect(self.single_shot_acquisition_requested) # Emit new signal
            print("ACQ_TAB: Connected single_acq_button -> single_shot_acquisition_requested")
        else:
            print("ACQ_TAB: Warning - single_acq_button (SINGLE) not found in UI.")
        # --- End connect SINGLE button ---

        # Connect Clear Button directly to DP5 controller
        if self.dp5_ctrl and hasattr(self.ui, 'clear_data_button'):
            self.ui.clear_data_button.clicked.connect(self.dp5_ctrl.clear_data)
            print("ACQ_TAB: Connected clear_data_button -> dp5_ctrl.clear_data")
        elif not hasattr(self.ui, 'clear_data_button'):
             print("ACQ_TAB: Warning - clear_data_button not found in UI.")

        # Connect Plot Controls (to internal slot)
        if hasattr(self.ui, 'lin_scale_radio'):
            self.ui.lin_scale_radio.toggled.connect(self.on_plot_scale_change)
            print("ACQ_TAB: Connected scale radios -> on_plot_scale_change")
        else: print("ACQ_TAB: Warning - lin_scale_radio not found in UI.")

    # --- Internal Slots ---
    def on_plot_scale_change(self):
        """Handles plot scale change radio buttons."""
        if not self.ui or not pg: return
        try:
            is_log = self.ui.log_scale_radio.isChecked()
            self.ui.plot_widget.setLogMode(y=is_log)
        except Exception as e:
            print(f"Error changing plot scale: {e}")

    # --- Public Slots for Updating UI from Controllers ---
    def update_minix_display(self, monitor_data):
        """Slot to update Mini-X monitor labels."""
        if not self.ui or not minix_api: return
        try:
            self.ui.minix_hv_monitor_display.setText(f"{monitor_data.mxmHighVoltage_kV:.2f}")
            self.ui.minix_current_monitor_display.setText(f"{monitor_data.mxmCurrent_uA:.1f}")
            temp_display_widget = getattr(self.ui, 'minix_board_temp_display', None)
            if temp_display_widget:
                 temp_display_widget.setText(f"{monitor_data.mxmTemperatureC:.1f}")
            self.ui.minix_power_display.setText(f"{monitor_data.mxmPower_mW:.1f}")
            status_text = minix_api.get_status_string(monitor_data.mxmStatusInd) #
            self.ui.minix_status_line_edit.setText(status_text)
            if hasattr(self.ui, 'set_minix_hv_indicator'):
                self.ui.set_minix_hv_indicator(bool(monitor_data.mxmHVOn))
        except AttributeError as e:
            print(f"Error accessing monitor_data fields or UI widgets in AcqTab: {e}")
            self.clear_minix_display(error=True)
        except Exception as e:
            print(f"Error updating MiniX monitor display in AcqTab: {e}")

    def clear_minix_display(self, error=False):
        """Clears the MiniX display labels."""
        if not self.ui: return
        default_text = "Error" if error else "N/A"
        self.ui.minix_hv_monitor_display.setText(default_text)
        self.ui.minix_current_monitor_display.setText(default_text)
        temp_display_widget = getattr(self.ui, 'minix_board_temp_display', None)
        if temp_display_widget: temp_display_widget.setText(default_text)
        self.ui.minix_power_display.setText(default_text)
        self.ui.minix_status_line_edit.setText("Disconnected" if not error else "Error")
        if hasattr(self.ui, 'set_minix_hv_indicator'):
            self.ui.set_minix_hv_indicator(False)

    def update_dp5_display(self, status_struct):
        """Updates the DP5 monitor labels."""
        if not self.ui: return
        try:
            def set_text(attr_name, text):
                 widget = getattr(self.ui, attr_name, None)
                 if widget: widget.setText(str(text))

            set_text("dp5_device_type_label", f"DP{status_struct.DEVICE_ID}" if status_struct.DEVICE_ID else "DP5/PX5") #
            set_text("dp5_serial_number_label", str(status_struct.SerialNumber)) #
            fw_major = status_struct.Firmware >> 4 #
            fw_minor = status_struct.Firmware & 0x0F #
            fw_build = status_struct.Build #
            fw_str = f"{fw_major}.{fw_minor:02d}" + (f".{fw_build:02d}" if fw_build > 0 else "")
            set_text("dp5_firmware_label", fw_str)
            fpga_major = status_struct.FPGA >> 4 #
            fpga_minor = status_struct.FPGA & 0x0F #
            set_text("dp5_fpga_label", f"{fpga_major}.{fpga_minor:02d}")
            set_text("dp5_fast_count_label", f"{status_struct.FastCount:,.0f}") #
            set_text("dp5_slow_count_label", f"{status_struct.SlowCount:,.0f}") #
            set_text("dp5_live_time_label", f"{status_struct.LiveTime:.1f}") #
            set_text("dp5_real_time_label", f"{status_struct.RealTime:.1f}") #
            det_temp_str = f"{status_struct.DET_TEMP:.1f} K" if status_struct.DET_TEMP > 0 else "N/A" #
            set_text("dp5_det_temp_label", det_temp_str)
            set_text("dp5_board_temp_label", f"{status_struct.DP5_TEMP:.1f} C") #
            set_text("dp5_hv_label", f"{status_struct.HV:.1f} V") #
        except AttributeError as e:
            print(f"Error accessing DP5 status fields in AcqTab: {e}")
            self.clear_dp5_display(error=True)
        except Exception as e:
            print(f"Error updating DP5 display in AcqTab: {e}")

    def clear_dp5_display(self, error=False):
        """Clears the DP5 monitor labels."""
        if not self.ui: return
        default_text = "Error" if error else "N/A"
        def set_text(attr_name, text):
             widget = getattr(self.ui, attr_name, None)
             if widget: widget.setText(str(text))

        set_text("dp5_device_type_label", default_text)
        set_text("dp5_serial_number_label", default_text)
        set_text("dp5_firmware_label", default_text)
        set_text("dp5_fpga_label", default_text)
        set_text("dp5_fast_count_label", default_text)
        set_text("dp5_slow_count_label", default_text)
        set_text("dp5_live_time_label", default_text)
        set_text("dp5_real_time_label", default_text)
        set_text("dp5_det_temp_label", default_text)
        set_text("dp5_board_temp_label", default_text)
        set_text("dp5_hv_label", default_text)

    def update_plot(self, spectrum_array):
        """Updates the spectrum plot."""
        if not self.ui or not pg or not hasattr(self.ui, 'plot_curve'): return
        try:
            if isinstance(spectrum_array, np.ndarray) and spectrum_array.ndim == 1:
                 if spectrum_array.size > 0:
                      x_data = np.arange(len(spectrum_array))
                      self.ui.plot_curve.setData(x=x_data, y=spectrum_array)
                 else:
                      self.clear_plot()
            elif spectrum_array is None:
                 self.clear_plot()
        except Exception as e:
            print(f"Error updating DP5 plot in AcqTab: {e}")

    def clear_plot(self):
         """Clears the DP5 plot."""
         if not self.ui or not pg or not hasattr(self.ui, 'plot_curve'): return
         try:
             self.ui.plot_curve.clear()
         except Exception as e:
             print(f"Error clearing plot in AcqTab: {e}")

    def update_state(self, dp5_connected, dp5_acquiring, sequence_running):
        """Updates the enabled state of widgets based on overall application state."""
        if not self.ui: return

        enable_while_sequence_idle = not sequence_running
        dp5_loaded = self.dp5_ctrl is not None

        # "Start Sequence" button
        self.ui.start_acq_button.setEnabled(dp5_loaded and dp5_connected and not dp5_acquiring and enable_while_sequence_idle)
        
        # "Stop Sequence/Acq" button - enabled if sequence is running OR if DP5 is acquiring (for single/manual stop)
        self.ui.stop_acq_button.setEnabled(dp5_loaded and (dp5_acquiring or sequence_running))
        
        # "SINGLE" button
        if hasattr(self.ui, 'single_acq_button'):
            self.ui.single_acq_button.setEnabled(dp5_loaded and dp5_connected and not dp5_acquiring and enable_while_sequence_idle)

        # "Clear DP5 Data" button
        self.ui.clear_data_button.setEnabled(dp5_loaded and dp5_connected and not dp5_acquiring and enable_while_sequence_idle)

        # Plot controls are always enabled if plot exists
        plot_exists = pg is not None
        self.ui.lin_scale_radio.setEnabled(plot_exists)
        self.ui.log_scale_radio.setEnabled(plot_exists)

        if not dp5_connected:
            self.clear_dp5_display()
            self.clear_plot()