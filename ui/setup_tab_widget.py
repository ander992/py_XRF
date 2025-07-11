# ui/setup_tab_widget.py
# Refactored QWidget class for the Setup Tab - Removed manual save button

# Keep imports (remove QPushButton if no longer needed elsewhere in this file)
from PyQt5.QtWidgets import (QWidget, QMessageBox, QFileDialog, QLabel,
                             QVBoxLayout)
try: from .setup_ui import Ui_SetupTab
except ImportError: Ui_SetupTab = None; print("Warning: ui.setup_ui not found.")

import os

class SetupTabWidget(QWidget):

    def __init__(self, minix_controller, dp5_controller, parent=None):
        super().__init__(parent)

        self.minix_ctrl = minix_controller
        self.dp5_ctrl = dp5_controller
        self.ui = None # Initialize ui attribute

        # Setup the UI defined in Ui_SetupTab
        if Ui_SetupTab:
            self.ui = Ui_SetupTab()
            self.ui.setupUi(self) # Populate this widget with the UI elements
            self._connect_signals()
        else:
            error_layout = QVBoxLayout(self)
            error_layout.addWidget(QLabel("Error: SetupTab UI definition failed to load."))

    def _connect_signals(self):
        """Connect signals from UI elements TO controller slots or internal methods."""
        if not self.ui: return

        # Mini-X Buttons (Keep as is)
        if self.minix_ctrl:
            self.ui.minix_connect_button.clicked.connect(self.minix_ctrl.connect_hardware)
            self.ui.minix_disconnect_button.clicked.connect(self.minix_ctrl.disconnect_hardware)
            self.ui.minix_set_hv_current_button.clicked.connect(self._ui_set_minix_hv_current)

        # DP5 Buttons
        if self.dp5_ctrl:
            self.ui.dp5_connect_button.clicked.connect(self.dp5_ctrl.connect)
            self.ui.dp5_disconnect_button.clicked.connect(self.dp5_ctrl.disconnect)
            self.ui.dp5_load_config_button.clicked.connect(self._ui_load_dp5_config)
            self.ui.dp5_choose_save_folder_button.clicked.connect(self._ui_choose_dp5_save_folder)

    # --- UI Helper Methods ---

    def _ui_set_minix_hv_current(self):
        if not self.ui: return
        if not self.minix_ctrl or not self.minix_ctrl.is_connected:
             return QMessageBox.warning(self, "Set Err", "MiniX not connected.")
        try:
            voltage = float(self.ui.minix_hv_set_input.text())
            current = float(self.ui.minix_current_set_input.text())
            self.minix_ctrl.set_hv_current(voltage, current)
        except ValueError: QMessageBox.warning(self, "Input Error", "Invalid MiniX voltage or current.")
        except AttributeError: QMessageBox.critical(self, "UI Error", "MiniX input fields not found.")


    def _ui_load_dp5_config(self):
        if not self.ui: return
        if not self.dp5_ctrl or not self.dp5_ctrl.is_connected: return QMessageBox.warning(self, "DP5 Error", "Connect DP5 first.")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_config_dir = os.path.normpath(os.path.join(script_dir, "..", "Help", "Configurations", "DET_CFG", "DP5"))
        if not os.path.isdir(default_config_dir): default_config_dir = os.path.dirname(script_dir)
        options = QFileDialog.Options() | QFileDialog.ReadOnly
        filePath, _ = QFileDialog.getOpenFileName(self, "Load DP5 Config", default_config_dir, "Config (*.txt);;All (*)", options=options)
        if filePath and self.dp5_ctrl:
            self.dp5_ctrl.load_config(filePath)

    def _ui_choose_dp5_save_folder(self):
        if not self.ui: return
        current_folder = self.ui.dp5_save_folder_display.text()
        start_dir = current_folder if current_folder and os.path.isdir(current_folder) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select DP5 Spectrum Save Folder", start_dir)
        if folder:
             self.ui.dp5_save_folder_display.setText(folder)


    def update_state(self, minix_connected, dp5_connected, sequence_running, dp5_acquiring, minix_ctrl_running, dp5_has_data):
        """Updates the enabled state of widgets based on overall application state."""
        if not self.ui: return

        enable_while_sequence_idle = not sequence_running
        minix_api_loaded = self.minix_ctrl is not None
        dp5_loaded = self.dp5_ctrl is not None

        # Mini-X Setup controls
        self.ui.minix_connect_button.setEnabled(minix_api_loaded and minix_ctrl_running and not minix_connected and enable_while_sequence_idle)
        self.ui.minix_disconnect_button.setEnabled(minix_api_loaded and minix_ctrl_running and minix_connected and enable_while_sequence_idle)
        can_set_minix = minix_api_loaded and minix_connected and enable_while_sequence_idle
        self.ui.minix_set_hv_current_button.setEnabled(can_set_minix)
        self.ui.minix_hv_set_input.setEnabled(can_set_minix)
        self.ui.minix_current_set_input.setEnabled(can_set_minix)
        self.ui.minix_continuous_checkbox.setEnabled(can_set_minix)

        # DP5 Setup controls
        self.ui.dp5_connect_button.setEnabled(dp5_loaded and not dp5_connected and enable_while_sequence_idle)
        self.ui.dp5_disconnect_button.setEnabled(dp5_loaded and dp5_connected and enable_while_sequence_idle)
        self.ui.dp5_load_config_button.setEnabled(dp5_loaded and dp5_connected and not dp5_acquiring and enable_while_sequence_idle)
        self.ui.dp5_choose_save_folder_button.setEnabled(enable_while_sequence_idle)

        # Acquisition Parameter controls
        self.ui.surface_width_input.setEnabled(enable_while_sequence_idle)
        self.ui.surface_height_input.setEnabled(enable_while_sequence_idle)
        self.ui.num_points_input.setEnabled(enable_while_sequence_idle)
        self.ui.time_per_point_input.setEnabled(enable_while_sequence_idle)
        if hasattr(self.ui, 'num_repetitions_input'):
            self.ui.num_repetitions_input.setEnabled(enable_while_sequence_idle)

    # --- Keep getter methods ---
    def get_acquisition_duration(self):
        # ... (keep implementation) ...
        if not self.ui: return None
        try: return float(self.ui.time_per_point_input.text())
        except (ValueError, AttributeError): return None

    def get_repetitions(self):
        # ... (keep implementation) ...
        if not self.ui or not hasattr(self.ui, 'num_repetitions_input'): return None
        try: return int(self.ui.num_repetitions_input.text())
        except (ValueError, AttributeError): return None

    def is_minix_continuous(self):
        # ... (keep implementation) ...
        if not self.ui: return False
        try: return self.ui.minix_continuous_checkbox.isChecked()
        except AttributeError: return False

    def get_save_folder(self):
        # ... (keep implementation) ...
        if not self.ui: return ""
        try: return self.ui.dp5_save_folder_display.text()
        except AttributeError: return ""