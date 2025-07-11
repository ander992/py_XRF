# main_app.py
# Main application window - Refactored to use Tab Widgets and SequenceManager

import os
import sys
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow,
                             QWidget, QTabWidget, QLabel,
                             QMessageBox, QVBoxLayout, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QEventLoop, pyqtSlot

# --- Import UI Widgets ---
try: from ui.setup_tab_widget import SetupTabWidget
except ImportError: SetupTabWidget = None; print("Warning: ui.setup_tab_widget.py not found.")
try: from ui.acquisition_tab_widget import AcquisitionTabWidget
except ImportError: AcquisitionTabWidget = None; print("Warning: ui.acquisition_tab_widget.py not found.")

# --- Import API Modules ---
try: from api import minix_api
except ImportError: minix_api = None; print("Warning: api.minix_api not found.")
except OSError as e: minix_api = None; print(f"Error loading MiniX API: {e}")
try: from api import dp5_api
except ImportError: dp5_api = None; print("Warning: api.dp5_api not found.")
except OSError as e: dp5_api = None; print(f"Error loading DP5 API: {e}")

# --- Import Controller Classes ---
try: from controllers.minix_controller import MiniXController
except ImportError: MiniXController = None; print("Warning: controllers.minix_controller not found.")
try: from controllers.dp5_controller import DP5Controller
except ImportError: DP5Controller = None; print("Warning: controllers.dp5_controller not found.")

# --- Import Logic Classes ---
try: from logic.sequence_manager import SequenceManager
except ImportError: SequenceManager = None; print("Warning: logic.sequence_manager.py not found.")
# Import the new SingleAcquisitionManager
try: from logic.single_acquistion_manager import SingleAcquisitionManager
except ImportError: SingleAcquisitionManager = None; print("Warning: logic.single_acquisition_manager.py not found.")


# --- Import Plotting Library ---
try: import pyqtgraph as pg
except ImportError: pg = None

# --- Main Window Class ---
class MainWindows(QMainWindow):
    def __init__(self):
        super().__init__()
        print("MAIN_APP: Initializing MainWindows...")

        self.setWindowTitle("PyXRF Controller (Refactored)")
        self.setGeometry(100, 100, 1100, 750)

        # --- Instantiate Controllers ---
        self.minix_ctrl = None
        if MiniXController and minix_api:
            print("MAIN_APP: Instantiating MiniXController...")
            self.minix_ctrl = MiniXController(parent=self)
            print("MAIN_APP: Attempting to start MiniX controller application automatically...")
            self.minix_ctrl.start_controller_app()
        else: print("MAIN_APP: MiniX Controller cannot be instantiated.")

        self.dp5_ctrl = None
        if DP5Controller and dp5_api:
            print("MAIN_APP: Instantiating DP5Controller...")
            self.dp5_ctrl = DP5Controller(parent=self)
        else: print("MAIN_APP: DP5 Controller cannot be instantiated.")

        # --- Instantiate Logic Managers ---
        self.sequence_manager = None
        if SequenceManager and self.minix_ctrl and self.dp5_ctrl:
             print("MAIN_APP: Instantiating SequenceManager...")
             self.sequence_manager = SequenceManager(self.minix_ctrl, self.dp5_ctrl, parent=self)
        else:
            print("MAIN_APP: Sequence Manager cannot be instantiated (check dependencies).")

        self.single_acq_manager = None
        if SingleAcquisitionManager and self.dp5_ctrl:
            print("MAIN_APP: Instantiating SingleAcquisitionManager...")
            self.single_acq_manager = SingleAcquisitionManager(self.dp5_ctrl, parent=self)
        else:
            print("MAIN_APP: Single Acquisition Manager cannot be instantiated (check dependencies).")


        # --- Central Widget (Tab Widget) ---
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().setExpanding(True)
        self.setCentralWidget(self.tab_widget)

        # --- Instantiate UI Tabs (using new Widget classes) ---
        self.setup_tab = None
        if SetupTabWidget:
             print("MAIN_APP: Instantiating SetupTabWidget...")
             self.setup_tab = SetupTabWidget(self.minix_ctrl, self.dp5_ctrl, self)
        else:
             fb_widget = QWidget(); layout = QVBoxLayout(fb_widget); layout.addWidget(QLabel("SetupTabWidget Load Error"))
             self.setup_tab = fb_widget

        self.acquisition_tab = None
        if AcquisitionTabWidget:
             print("MAIN_APP: Instantiating AcquisitionTabWidget...")
             self.acquisition_tab = AcquisitionTabWidget(self.minix_ctrl, self.dp5_ctrl, self)
        else:
             fb_widget = QWidget(); layout = QVBoxLayout(fb_widget); layout.addWidget(QLabel("AcquisitionTabWidget Load Error"))
             self.acquisition_tab = fb_widget

        # Analysis Tab (Still placeholder)
        self.analysis_tab = QWidget()
        layout3 = QVBoxLayout(self.analysis_tab)
        layout3.addWidget(QLabel("Future Implementation: Analysis"))

        # Add actual tab widgets to the QTabWidget
        if self.setup_tab: self.tab_widget.addTab(self.setup_tab, "Setup")
        if self.acquisition_tab: self.tab_widget.addTab(self.acquisition_tab, "Acquisition")
        self.tab_widget.addTab(self.analysis_tab, "Analysis")


        # --- Status Bar ---
        self.statusBar().showMessage("Ready.")

        # --- Connect Signals ---
        print("MAIN_APP: Connecting signals...")
        self._connect_signals()

        # --- Initial State ---
        print("MAIN_APP: Scheduling initial UI update.")
        QTimer.singleShot(100, self._update_ui_state)
        print("MAIN_APP: Initialization complete.")


    def _connect_signals(self):
        """ Connect signals between components. """
        print("MAIN_APP: _connect_signals executing...")

        # --- Controller -> Main Window / Tab Widgets ---
        if self.minix_ctrl:
            print("MAIN_APP: Connecting MiniX controller signals...")
            self.minix_ctrl.connection_changed.connect(self._update_ui_state)
            self.minix_ctrl.controller_running_changed.connect(self._update_ui_state)
            self.minix_ctrl.hv_state_changed.connect(self._update_ui_state)
            self.minix_ctrl.error_occurred.connect(self.handle_minix_error)
            self.minix_ctrl.status_message.connect(self.handle_status_message)
            if self.acquisition_tab and hasattr(self.acquisition_tab, 'update_minix_display'):
                 self.minix_ctrl.monitor_data_updated.connect(self.acquisition_tab.update_minix_display)

        if self.dp5_ctrl:
            print("MAIN_APP: Connecting DP5 controller signals...")
            self.dp5_ctrl.connection_changed.connect(self._update_ui_state)
            self.dp5_ctrl.acquisition_state_changed.connect(self._update_ui_state) # Crucial for UI updates
            self.dp5_ctrl.error_occurred.connect(self.handle_dp5_error)
            self.dp5_ctrl.status_message.connect(self.handle_status_message)
            if self.acquisition_tab:
                 if hasattr(self.acquisition_tab, 'update_dp5_display'):
                      self.dp5_ctrl.status_updated.connect(self.acquisition_tab.update_dp5_display)
                 if hasattr(self.acquisition_tab, 'update_plot'):
                      self.dp5_ctrl.spectrum_updated.connect(self.acquisition_tab.update_plot)

        # --- Sequence Manager -> Main Window ---
        if self.sequence_manager:
             print("MAIN_APP: Connecting SequenceManager signals...")
             self.sequence_manager.status_update.connect(self.handle_status_message)
             self.sequence_manager.sequence_started.connect(self._update_ui_state)
             self.sequence_manager.sequence_finished.connect(self._update_ui_state)
             self.sequence_manager.sequence_aborted.connect(self._update_ui_state)
             self.sequence_manager.request_safe_hv_on.connect(self._safe_minix_hv_on)

        # --- Single Acquisition Manager -> Main Window ---
        if self.single_acq_manager:
            print("MAIN_APP: Connecting SingleAcquisitionManager signals...")
            self.single_acq_manager.status_update.connect(self.handle_status_message)
            self.single_acq_manager.acquisition_started.connect(self._update_ui_state)
            self.single_acq_manager.acquisition_finished.connect(self._update_ui_state_after_single_acq)
            self.single_acq_manager.acquisition_aborted.connect(self._update_ui_state_after_single_acq_abort)


        # --- UI -> Main Window / Managers ---
        if self.acquisition_tab:
            print("MAIN_APP: Connecting AcquisitionTabWidget signals...")
            if hasattr(self.acquisition_tab, 'single_acquisition_start_requested'): # "Start Sequence" button
                 self.acquisition_tab.single_acquisition_start_requested.connect(self._ui_start_sequence)
                 print("MAIN_APP: Connected acq_tab.start_requested (Start Sequence) -> _ui_start_sequence")
            else:
                 print("MAIN_APP: Warning: AcquisitionTabWidget missing 'single_acquisition_start_requested' signal.")

            if hasattr(self.acquisition_tab, 'single_acquisition_stop_requested'): # "Stop Sequence/Acq" button
                 self.acquisition_tab.single_acquisition_stop_requested.connect(self._ui_stop_all_acquisitions)
                 print("MAIN_APP: Connected acq_tab.stop_requested (Stop Sequence/Acq) -> _ui_stop_all_acquisitions")
            else:
                 print("MAIN_APP: Warning: AcquisitionTabWidget missing 'single_acquisition_stop_requested' signal.")

            if hasattr(self.acquisition_tab, 'single_shot_acquisition_requested'): # "SINGLE" button
                self.acquisition_tab.single_shot_acquisition_requested.connect(self._ui_start_single_shot_acquisition)
                print("MAIN_APP: Connected acq_tab.single_shot_acquisition_requested -> _ui_start_single_shot_acquisition")
            else:
                print("MAIN_APP: Warning: AcquisitionTabWidget missing 'single_shot_acquisition_requested' signal.")


    # --- Main Window Slots / Methods ---

    def _update_ui_state(self):
        """ Gathers state and tells Tab Widgets to update their UI elements. """
        print("MAIN_APP: _update_ui_state called...")
        minix_ctrl_running = self.minix_ctrl.is_controller_app_running if self.minix_ctrl else False
        minix_connected = self.minix_ctrl.is_connected if self.minix_ctrl else False
        dp5_connected = self.dp5_ctrl.is_connected if self.dp5_ctrl else False
        
        # Check DP5 acquiring state from dp5_ctrl
        dp5_acquiring_direct = self.dp5_ctrl.is_acquiring if self.dp5_ctrl else False
        
        # Check sequence running states
        sequence_manager_running = self.sequence_manager.is_running if self.sequence_manager else False
        single_acq_manager_running = self.single_acq_manager.is_running if self.single_acq_manager else False
        
        # Overall acquisition active if DP5 is directly acquiring OR any manager says it's running a sequence/acquisition
        is_overall_acquisition_active = dp5_acquiring_direct or sequence_manager_running or single_acq_manager_running

        print(f"MAIN_APP: States: minix_run={minix_ctrl_running}, minix_conn={minix_connected}, dp5_conn={dp5_connected}, dp5_acq_direct={dp5_acquiring_direct}, seq_mgr_run={sequence_manager_running}, single_acq_run={single_acq_manager_running}, overall_acq_active={is_overall_acquisition_active}")

        dp5_has_data = self.dp5_ctrl._last_spectrum_data is not None if self.dp5_ctrl else False

        if self.setup_tab and hasattr(self.setup_tab, 'update_state'):
             print("MAIN_APP: Updating Setup Tab state...")
             self.setup_tab.update_state(minix_connected, dp5_connected, is_overall_acquisition_active, dp5_acquiring_direct, minix_ctrl_running, dp5_has_data)

        if self.acquisition_tab and hasattr(self.acquisition_tab, 'update_state'):
             print("MAIN_APP: Updating Acquisition Tab state...")
             self.acquisition_tab.update_state(dp5_connected, is_overall_acquisition_active, is_overall_acquisition_active)


    def _ui_start_sequence(self):
        """Reads parameters from SetupTabWidget and starts the sequence via SequenceManager."""
        print("MAIN_APP: _ui_start_sequence called...")
        if not self.sequence_manager:
             QMessageBox.critical(self, "Error", "Sequence Manager not initialized.")
             return
        if self.single_acq_manager and self.single_acq_manager.is_running:
            QMessageBox.warning(self, "Busy", "Cannot start sequence while single acquisition is running.")
            return
        if not self.setup_tab or not hasattr(self.setup_tab, 'get_repetitions'):
             QMessageBox.critical(self, "Error", "Setup Tab not initialized correctly.")
             return

        repetitions = self.setup_tab.get_repetitions()
        duration = self.setup_tab.get_acquisition_duration()
        minix_continuous = self.setup_tab.is_minix_continuous()
        save_folder = self.setup_tab.get_save_folder()
        print(f"MAIN_APP: Read sequence params: reps={repetitions}, dur={duration}, cont={minix_continuous}, folder='{save_folder}'")

        print("MAIN_APP: Calling sequence_manager.start_sequence...")
        start_success = self.sequence_manager.start_sequence(repetitions, duration, minix_continuous, save_folder)
        print(f"MAIN_APP: sequence_manager.start_sequence returned: {start_success}")
        self._update_ui_state()

    def _ui_start_single_shot_acquisition(self):
        """Handles the request for a single DP5 acquisition and save."""
        print("MAIN_APP: _ui_start_single_shot_acquisition called...")
        if not self.single_acq_manager:
            QMessageBox.critical(self, "Error", "Single Acquisition Manager not initialized.")
            return
        if self.sequence_manager and self.sequence_manager.is_running:
            QMessageBox.warning(self, "Busy", "Cannot start single acquisition while sequence is running.")
            return
        if self.single_acq_manager.is_running:
            QMessageBox.information(self, "Info", "Single acquisition is already in progress.")
            return
        if not self.dp5_ctrl or not self.dp5_ctrl.is_connected:
            QMessageBox.warning(self, "Error", "DP5 is not connected.")
            return

        # Get acquisition duration
        duration, ok = QInputDialog.getDouble(self, "Single Acquisition Duration", "Enter duration (seconds):", 60.0, 0.1, 36000.0, 1)
        if not ok or duration <= 0:
            self.handle_status_message("Single acquisition cancelled by user or invalid duration.")
            return

        # Get save file path
        default_save_dir = self.setup_tab.get_save_folder() if self.setup_tab else os.path.expanduser("~")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = os.path.join(default_save_dir, f"single_spectrum_{timestamp}.mca")
        
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        save_filepath, _ = QFileDialog.getSaveFileName(self, "Save Spectrum As...", default_filename, "MCA Files (*.mca);;All Files (*)", options=options)

        if not save_filepath:
            self.handle_status_message("Single acquisition cancelled by user (no save path selected).")
            return
        
        # Ensure .mca extension if not provided
        if not save_filepath.lower().endswith(".mca"):
            save_filepath += ".mca"

        self.handle_status_message(f"Starting single acquisition: {duration}s, saving to {os.path.basename(save_filepath)}")
        self.single_acq_manager.start_acquisition_and_save(duration, save_filepath)
        self._update_ui_state()


    def _ui_stop_all_acquisitions(self):
        """Stops any running acquisition (sequence or single shot)."""
        print("MAIN_APP: _ui_stop_all_acquisitions called.")
        stopped_something = False
        if self.sequence_manager and self.sequence_manager.is_running:
            print("MAIN_APP: Stopping sequence...")
            self.sequence_manager.stop_sequence("Stopped by user from UI")
            stopped_something = True
        
        if self.single_acq_manager and self.single_acq_manager.is_running:
            print("MAIN_APP: Stopping single acquisition...")
            self.single_acq_manager.stop_acquisition("Stopped by user from UI")
            stopped_something = True
        
        # Fallback: If managers claim not running, but DP5 controller is acquiring
        if not stopped_something and self.dp5_ctrl and self.dp5_ctrl.is_acquiring:
            print("MAIN_APP: DP5 is acquiring directly, stopping DP5 controller.")
            self.dp5_ctrl.stop_acquisition()
            stopped_something = True
            
        if not stopped_something:
            self.handle_status_message("No acquisition running to stop.")
        
        self._update_ui_state()


    def _update_ui_state_after_single_acq(self, success):
        """Called when single acquisition finishes or is aborted."""
        print(f"MAIN_APP: _update_ui_state_after_single_acq called, success: {success}")
        if success:
            self.handle_status_message("Single acquisition and save completed.")
        else:
            # Error message should have been set by the manager via status_update or abort signal
            QMessageBox.warning(self, "Single Acquisition Failed", f"Single acquisition failed or was aborted. Reason: {self.single_acq_manager._error_reason if self.single_acq_manager else 'Unknown'}")
        self._update_ui_state()

    def _update_ui_state_after_single_acq_abort(self, reason):
        """Called specifically when single acquisition is aborted."""
        print(f"MAIN_APP: _update_ui_state_after_single_acq_abort called, reason: {reason}")
        QMessageBox.warning(self, "Single Acquisition Aborted", f"Single acquisition aborted: {reason}")
        self._update_ui_state()


    def handle_status_message(self, message):
        """Shows message in status bar."""
        print(f"MAIN_APP: Status Message: {message}")
        self.statusBar().showMessage(message, 5000)

    def handle_minix_error(self, message):
        """Handles errors reported by the MiniX controller."""
        print(f"MAIN_APP: Handling MiniX Error: {message}")
        QMessageBox.warning(self, "MiniX Error", message)
        self.statusBar().showMessage(f"MiniX Error: {message}", 6000)
        if self.sequence_manager and self.sequence_manager.is_running:
            print("MAIN_APP: Aborting sequence due to MiniX error.")
            self.sequence_manager.stop_sequence(f"MiniX Error: {message}")
        # MiniX error doesn't directly stop single_acq_manager as it doesn't use MiniX
        self._update_ui_state()

    def handle_dp5_error(self, message):
        """Handles errors reported by the DP5 controller."""
        print(f"MAIN_APP: Handling DP5 Error: {message}")
        QMessageBox.warning(self, "DP5 Error", message)
        self.statusBar().showMessage(f"DP5 Error: {message}", 6000)
        if self.sequence_manager and self.sequence_manager.is_running:
            print("MAIN_APP: Aborting sequence due to DP5 error.")
            self.sequence_manager.stop_sequence(f"DP5 Error: {message}")
        if self.single_acq_manager and self.single_acq_manager.is_running:
            print("MAIN_APP: Aborting single acquisition due to DP5 error.")
            self.single_acq_manager.stop_acquisition(f"DP5 Error: {message}")
        self._update_ui_state()

    @pyqtSlot()
    def _safe_minix_hv_on(self, called_by_sequence=True):
        """Turns MiniX HV ON after user confirmation. Triggered by SequenceManager."""
        print(f"MAIN_APP: _safe_minix_hv_on called (called_by_sequence={called_by_sequence})")
        if not self.minix_ctrl or not self.minix_ctrl.is_connected:
             msg = "MiniX not connected. Cannot turn HV ON."
             print(f"MAIN_APP: HV ON Check Failed: {msg}")
             QMessageBox.warning(self, "HV Error", msg)
             if called_by_sequence and self.sequence_manager and self.sequence_manager.is_running:
                  self.sequence_manager.stop_sequence(msg)
             return False

        ask_user = True
        should_turn_on = False
        if ask_user:
             prompt = "Sequence requesting MiniX HV ON. Proceed?" if called_by_sequence else "Turn MiniX HV ON?"
             print("MAIN_APP: Asking user confirmation for HV ON...")
             reply = QMessageBox.warning(self, "SAFETY WARNING", prompt,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
             should_turn_on = (reply == QMessageBox.Yes)
             print(f"MAIN_APP: User reply: {reply} (Yes={QMessageBox.Yes}) -> Should turn on: {should_turn_on}")
        else:
             should_turn_on = True

        success = False
        if should_turn_on and self.minix_ctrl:
             print("MAIN_APP: Calling minix_ctrl.set_hv_on()")
             self.minix_ctrl.set_hv_on()
             success = True
        elif not should_turn_on and called_by_sequence:
             msg = "User cancelled HV ON request. Aborting sequence."
             print(f"MAIN_APP: {msg}")
             self.handle_status_message(msg)
             if self.sequence_manager: self.sequence_manager.stop_sequence("User cancelled HV ON")
             success = False

        print(f"MAIN_APP: _safe_minix_hv_on returning {success}")
        return success


    def closeEvent(self, event):
        """Handles window closing event, ensuring cleanup."""
        print("MAIN_APP: closeEvent triggered.")
        user_wants_to_close = True

        if (self.sequence_manager and self.sequence_manager.is_running) or \
           (self.single_acq_manager and self.single_acq_manager.is_running):
            print("MAIN_APP: Acquisition running, asking user to stop...")
            reply = QMessageBox.question(self, "Acquisition Running",
                                         "An acquisition is currently running. Stop it and exit?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                print("MAIN_APP: Stopping acquisitions due to close event...")
                if self.sequence_manager: self.sequence_manager.stop_sequence("Application closing")
                if self.single_acq_manager: self.single_acq_manager.stop_acquisition("Application closing")
                self._wait_with_events(200) 
            else:
                print("MAIN_APP: Close event ignored, acquisition continues.")
                user_wants_to_close = False
                event.ignore()
                return

        if user_wants_to_close:
            print("MAIN_APP: Proceeding with shutdown...")
            if self.dp5_ctrl:
                print("MAIN_APP: Disconnecting DP5...")
                self.dp5_ctrl.disconnect()

            if self.minix_ctrl:
                print("MAIN_APP: Closing MiniX controller app...")
                self.minix_ctrl.close_controller_app()
                time.sleep(0.5) 

            print("MAIN_APP: Accepting close event."); event.accept()

    def _wait_with_events(self, duration_ms):
         """Pauses execution for a duration while keeping the UI responsive."""
         if duration_ms <= 0: return
         loop = QEventLoop()
         QTimer.singleShot(duration_ms, loop.quit)
         loop.exec_()

# --- Main Execution Block ---
if __name__ == "__main__":
    print("MAIN_APP: Starting application...")
    if pg is None: print("ERROR: pyqtgraph is required but not found.")
    if not SequenceManager: print("ERROR: SequenceManager class not found.")
    if not SingleAcquisitionManager: print("ERROR: SingleAcquisitionManager class not found.")
    if not SetupTabWidget: print("ERROR: SetupTabWidget class not found.")
    if not AcquisitionTabWidget: print("ERROR: AcquisitionTabWidget class not found.")

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    print("MAIN_APP: Creating QApplication...")
    app = QApplication(sys.argv)
    print("MAIN_APP: Creating MainWindows...")
    main_window = MainWindows()
    print("MAIN_APP: Showing MainWindows...")
    main_window.show()
    print("MAIN_APP: Starting QApplication event loop...")
    sys.exit(app.exec_())