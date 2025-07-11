# py_xrf/ui/acquisition_ui.py
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5.QtCore import QSize, Qt

try:
    import pyqtgraph as pg
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    print("Warning: pyqtgraph not found. Plotting will be disabled.")
    pg = None
    PYQTGRAPH_AVAILABLE = False

class LedIndicator(QWidget):
    """ A simple round LED indicator widget """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(20, 20))
        self.setMaximumSize(QSize(20, 20))
        self._is_on = False
        self._on_color = QColor("lime")
        self._off_color = QColor("darkRed")

    def set_state(self, is_on):
        is_on = bool(is_on)
        if self._is_on != is_on:
            self._is_on = is_on
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = self._on_color if self._is_on else self._off_color
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))


class Ui_AcquisitionTab(object):
    def setupUi(self, AcquisitionTabWidget):
        AcquisitionTabWidget.setObjectName("AcquisitionTabWidget")

        # --- Main Layout: Plot on Left, Controls/Monitors on Right ---
        self.main_layout = QtWidgets.QHBoxLayout(AcquisitionTabWidget)
        self.main_layout.setObjectName("main_layout")
        self.left_panel_layout = QtWidgets.QVBoxLayout()
        self.left_panel_layout.setObjectName("left_panel_layout")
        self.right_panel_layout = QtWidgets.QVBoxLayout()
        self.right_panel_layout.setSpacing(10)
        self.right_panel_layout.setObjectName("right_panel_layout")

        # --- Left Panel: Plot and Plot Controls ---
        self.plot_group = QtWidgets.QGroupBox(AcquisitionTabWidget)
        self.plot_group.setObjectName("plot_group")
        self.plot_layout = QtWidgets.QVBoxLayout(self.plot_group)
        self.plot_layout.setObjectName("plot_layout")

        if PYQTGRAPH_AVAILABLE:
            self.plot_widget = pg.PlotWidget(self.plot_group)
            self.plot_widget.setObjectName("plot_widget")
            # self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('left', 'Counts')
            self.plot_widget.setLabel('bottom', 'Channel')
            self.plot_curve = self.plot_widget.plot(pen='r')
            self.plot_layout.addWidget(self.plot_widget)
        else:
            self.plot_missing_label = QtWidgets.QLabel(self.plot_group)
            self.plot_missing_label.setText("Plotting requires pyqtgraph (not found)")
            self.plot_missing_label.setAlignment(QtCore.Qt.AlignCenter)
            self.plot_layout.addWidget(self.plot_missing_label)

        self.plot_controls_group = QtWidgets.QGroupBox(AcquisitionTabWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plot_controls_group.sizePolicy().hasHeightForWidth())
        self.plot_controls_group.setSizePolicy(sizePolicy)
        self.plot_controls_group.setObjectName("plot_controls_group")
        self.plot_controls_layout = QtWidgets.QHBoxLayout(self.plot_controls_group)
        self.plot_controls_layout.setObjectName("plot_controls_layout")
        self.lin_scale_radio = QtWidgets.QRadioButton(self.plot_controls_group)
        self.lin_scale_radio.setChecked(True)
        self.lin_scale_radio.setObjectName("lin_scale_radio")
        self.plot_controls_layout.addWidget(self.lin_scale_radio)
        self.log_scale_radio = QtWidgets.QRadioButton(self.plot_controls_group)
        self.log_scale_radio.setObjectName("log_scale_radio")
        self.plot_controls_layout.addWidget(self.log_scale_radio)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.plot_controls_layout.addItem(spacerItem)
        self.left_panel_layout.addWidget(self.plot_group)
        self.left_panel_layout.addWidget(self.plot_controls_group)
        self.main_layout.addLayout(self.left_panel_layout, 70)

        # --- Right Panel: Acquisition, Mini-X Monitor, DP5 Monitor ---
        # -- Acquisition Group --
        self.acq_group = QtWidgets.QGroupBox(AcquisitionTabWidget) # Parent is AcquisitionTabWidget
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.acq_group.sizePolicy().hasHeightForWidth())
        self.acq_group.setSizePolicy(sizePolicy)
        self.acq_group.setObjectName("acq_group")
        self.acq_layout = QtWidgets.QHBoxLayout(self.acq_group)
        self.acq_layout.setObjectName("acq_layout")

        self.start_acq_button = QtWidgets.QPushButton(self.acq_group)
        self.start_acq_button.setObjectName("start_acq_button")
        self.acq_layout.addWidget(self.start_acq_button)

        self.stop_acq_button = QtWidgets.QPushButton(self.acq_group)
        self.stop_acq_button.setObjectName("stop_acq_button")
        self.acq_layout.addWidget(self.stop_acq_button)
        
        # New SINGLE button
        self.single_acq_button = QtWidgets.QPushButton(self.acq_group)
        self.single_acq_button.setObjectName("single_acq_button")
        self.acq_layout.addWidget(self.single_acq_button)

        self.clear_data_button = QtWidgets.QPushButton(self.acq_group)
        self.clear_data_button.setObjectName("clear_data_button")
        self.acq_layout.addWidget(self.clear_data_button)
        self.right_panel_layout.addWidget(self.acq_group) # Add group to right panel

        # -- Mini-X Monitor Group --
        self.minix_monitor_group = QtWidgets.QGroupBox(AcquisitionTabWidget)
        self.minix_monitor_group.setObjectName("minix_monitor_group")
        self.minix_monitor_layout = QtWidgets.QGridLayout(self.minix_monitor_group)
        self.minix_monitor_layout.setObjectName("minix_monitor_layout")
        # Row 0
        self.label_minix_volt = QtWidgets.QLabel(self.minix_monitor_group)
        self.label_minix_volt.setObjectName("label_minix_volt")
        self.minix_monitor_layout.addWidget(self.label_minix_volt, 0, 0, 1, 1)
        self.minix_hv_monitor_display = QtWidgets.QLabel(self.minix_monitor_group)
        self.minix_hv_monitor_display.setObjectName("minix_hv_monitor_display")
        self.minix_monitor_layout.addWidget(self.minix_hv_monitor_display, 0, 1, 1, 1)
        # Row 1
        self.label_minix_curr = QtWidgets.QLabel(self.minix_monitor_group)
        self.label_minix_curr.setObjectName("label_minix_curr")
        self.minix_monitor_layout.addWidget(self.label_minix_curr, 1, 0, 1, 1)
        self.minix_current_monitor_display = QtWidgets.QLabel(self.minix_monitor_group)
        self.minix_current_monitor_display.setObjectName("minix_current_monitor_display")
        self.minix_monitor_layout.addWidget(self.minix_current_monitor_display, 1, 1, 1, 1)
        # Row 2
        self.label_minix_temp = QtWidgets.QLabel(self.minix_monitor_group)
        self.label_minix_temp.setObjectName("label_minix_temp")
        self.minix_monitor_layout.addWidget(self.label_minix_temp, 2, 0, 1, 1)
        self.minix_board_temp_display = QtWidgets.QLabel(self.minix_monitor_group)
        self.minix_board_temp_display.setObjectName("minix_board_temp_display")
        self.minix_monitor_layout.addWidget(self.minix_board_temp_display, 2, 1, 1, 1)
        # Row 3
        self.label_minix_power = QtWidgets.QLabel(self.minix_monitor_group)
        self.label_minix_power.setObjectName("label_minix_power")
        self.minix_monitor_layout.addWidget(self.label_minix_power, 3, 0, 1, 1)
        self.minix_power_display = QtWidgets.QLabel(self.minix_monitor_group)
        self.minix_power_display.setObjectName("minix_power_display")
        self.minix_monitor_layout.addWidget(self.minix_power_display, 3, 1, 1, 1)
        # Row 4
        self.label_minix_status = QtWidgets.QLabel(self.minix_monitor_group)
        self.label_minix_status.setObjectName("label_minix_status")
        self.minix_monitor_layout.addWidget(self.label_minix_status, 4, 0, 1, 1)
        self.minix_status_line_edit = QtWidgets.QLineEdit(self.minix_monitor_group)
        self.minix_status_line_edit.setReadOnly(True)
        self.minix_status_line_edit.setObjectName("minix_status_line_edit")
        self.minix_monitor_layout.addWidget(self.minix_status_line_edit, 4, 1, 1, 1)
        # Row 5: HV On Indicator LED
        self.minix_hv_indicator_layout = QtWidgets.QHBoxLayout()
        self.minix_hv_indicator_layout.setObjectName("minix_hv_indicator_layout")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.minix_hv_indicator_layout.addItem(spacerItem1)
        # Create LedIndicator instance here
        self.minix_hv_indicator_led = LedIndicator(self.minix_monitor_group)
        self.minix_hv_indicator_led.setObjectName("minix_hv_indicator_led")
        self.minix_hv_indicator_layout.addWidget(self.minix_hv_indicator_led)
        self.minix_hv_indicator_label = QtWidgets.QLabel(self.minix_monitor_group)
        self.minix_hv_indicator_label.setObjectName("minix_hv_indicator_label")
        self.minix_hv_indicator_layout.addWidget(self.minix_hv_indicator_label)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.minix_hv_indicator_layout.addItem(spacerItem2)
        self.minix_monitor_layout.addLayout(self.minix_hv_indicator_layout, 5, 0, 1, 2)

        self.right_panel_layout.addWidget(self.minix_monitor_group) # Add group to right panel

        # -- DP5 Monitor Group --
        self.dp5_monitor_group = QtWidgets.QGroupBox(AcquisitionTabWidget) # Parent is AcquisitionTabWidget
        self.dp5_monitor_group.setObjectName("dp5_monitor_group")
        self.dp5_monitor_layout = QtWidgets.QGridLayout(self.dp5_monitor_group)
        self.dp5_monitor_layout.setObjectName("dp5_monitor_layout")
        # Row 0
        self.label_dp5_type = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_type.setObjectName("label_dp5_type")
        self.dp5_monitor_layout.addWidget(self.label_dp5_type, 0, 0, 1, 1)
        self.dp5_device_type_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_device_type_label.setObjectName("dp5_device_type_label")
        self.dp5_monitor_layout.addWidget(self.dp5_device_type_label, 0, 1, 1, 1)
        # Row 1
        self.label_dp5_sn = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_sn.setObjectName("label_dp5_sn")
        self.dp5_monitor_layout.addWidget(self.label_dp5_sn, 1, 0, 1, 1)
        self.dp5_serial_number_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_serial_number_label.setObjectName("dp5_serial_number_label")
        self.dp5_monitor_layout.addWidget(self.dp5_serial_number_label, 1, 1, 1, 1)
        # Row 2
        self.label_dp5_fw = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_fw.setObjectName("label_dp5_fw")
        self.dp5_monitor_layout.addWidget(self.label_dp5_fw, 2, 0, 1, 1)
        self.dp5_firmware_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_firmware_label.setObjectName("dp5_firmware_label")
        self.dp5_monitor_layout.addWidget(self.dp5_firmware_label, 2, 1, 1, 1)
        # Row 3
        self.label_dp5_fpga = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_fpga.setObjectName("label_dp5_fpga")
        self.dp5_monitor_layout.addWidget(self.label_dp5_fpga, 3, 0, 1, 1)
        self.dp5_fpga_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_fpga_label.setObjectName("dp5_fpga_label")
        self.dp5_monitor_layout.addWidget(self.dp5_fpga_label, 3, 1, 1, 1)
        # Row 4: Line Separator
        self.line1 = QtWidgets.QFrame(self.dp5_monitor_group)
        self.line1.setFrameShape(QtWidgets.QFrame.HLine)
        self.line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line1.setObjectName("line1")
        self.dp5_monitor_layout.addWidget(self.line1, 4, 0, 1, 2) # Span 2 cols
        # Row 5
        self.label_dp5_fast = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_fast.setObjectName("label_dp5_fast")
        self.dp5_monitor_layout.addWidget(self.label_dp5_fast, 5, 0, 1, 1)
        self.dp5_fast_count_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_fast_count_label.setObjectName("dp5_fast_count_label")
        self.dp5_monitor_layout.addWidget(self.dp5_fast_count_label, 5, 1, 1, 1)
        # Row 6
        self.label_dp5_slow = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_slow.setObjectName("label_dp5_slow")
        self.dp5_monitor_layout.addWidget(self.label_dp5_slow, 6, 0, 1, 1)
        self.dp5_slow_count_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_slow_count_label.setObjectName("dp5_slow_count_label")
        self.dp5_monitor_layout.addWidget(self.dp5_slow_count_label, 6, 1, 1, 1)
        # Row 7
        self.label_dp5_live = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_live.setObjectName("label_dp5_live")
        self.dp5_monitor_layout.addWidget(self.label_dp5_live, 7, 0, 1, 1)
        self.dp5_live_time_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_live_time_label.setObjectName("dp5_live_time_label")
        self.dp5_monitor_layout.addWidget(self.dp5_live_time_label, 7, 1, 1, 1)
        # Row 8
        self.label_dp5_real = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_real.setObjectName("label_dp5_real")
        self.dp5_monitor_layout.addWidget(self.label_dp5_real, 8, 0, 1, 1)
        self.dp5_real_time_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_real_time_label.setObjectName("dp5_real_time_label")
        self.dp5_monitor_layout.addWidget(self.dp5_real_time_label, 8, 1, 1, 1)
        # Row 9: Line Separator
        self.line2 = QtWidgets.QFrame(self.dp5_monitor_group)
        self.line2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line2.setObjectName("line2")
        self.dp5_monitor_layout.addWidget(self.line2, 9, 0, 1, 2) # Span 2 cols
        # Row 10
        self.label_dp5_det_temp = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_det_temp.setObjectName("label_dp5_det_temp")
        self.dp5_monitor_layout.addWidget(self.label_dp5_det_temp, 10, 0, 1, 1)
        self.dp5_det_temp_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_det_temp_label.setObjectName("dp5_det_temp_label")
        self.dp5_monitor_layout.addWidget(self.dp5_det_temp_label, 10, 1, 1, 1)
        # Row 11
        self.label_dp5_board_temp = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_board_temp.setObjectName("label_dp5_board_temp")
        self.dp5_monitor_layout.addWidget(self.label_dp5_board_temp, 11, 0, 1, 1)
        self.dp5_board_temp_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_board_temp_label.setObjectName("dp5_board_temp_label")
        self.dp5_monitor_layout.addWidget(self.dp5_board_temp_label, 11, 1, 1, 1)
        # Row 12
        self.label_dp5_hv = QtWidgets.QLabel(self.dp5_monitor_group)
        self.label_dp5_hv.setObjectName("label_dp5_hv")
        self.dp5_monitor_layout.addWidget(self.label_dp5_hv, 12, 0, 1, 1)
        self.dp5_hv_label = QtWidgets.QLabel(self.dp5_monitor_group)
        self.dp5_hv_label.setObjectName("dp5_hv_label")
        self.dp5_monitor_layout.addWidget(self.dp5_hv_label, 12, 1, 1, 1)

        # Set column stretch for DP5 monitor grid (optional, for alignment)
        self.dp5_monitor_layout.setColumnStretch(1, 1)

        self.right_panel_layout.addWidget(self.dp5_monitor_group) # Add group to right panel

        # Add Stretch to push groups up
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.right_panel_layout.addItem(spacerItem3)

        # --- Add Panels to Main Layout ---
        self.main_layout.addLayout(self.right_panel_layout, 30) # Monitors/Controls take less (30%)

        self.retranslateUi(AcquisitionTabWidget) # Call retranslateUi
        QtCore.QMetaObject.connectSlotsByName(AcquisitionTabWidget) # Needed if using slots by name

    def retranslateUi(self, AcquisitionTabWidget):
        _translate = QtCore.QCoreApplication.translate
        AcquisitionTabWidget.setWindowTitle(_translate("AcquisitionTabWidget", "Form")) # Or remove if title set elsewhere

        # Left Panel
        self.plot_group.setTitle(_translate("AcquisitionTabWidget", "Spectrum"))
        self.plot_controls_group.setTitle(_translate("AcquisitionTabWidget", "Plot Controls"))
        self.lin_scale_radio.setText(_translate("AcquisitionTabWidget", "Linear"))
        self.log_scale_radio.setText(_translate("AcquisitionTabWidget", "Log"))

        # Right Panel
        self.acq_group.setTitle(_translate("AcquisitionTabWidget", "DP5 Acquisition Control"))
        self.start_acq_button.setText(_translate("AcquisitionTabWidget", "Start Sequence")) # Changed label for clarity
        self.stop_acq_button.setText(_translate("AcquisitionTabWidget", "Stop Sequence/Acq")) # Changed label for clarity
        if hasattr(self, 'single_acq_button'): # Check if button exists before setting text
            self.single_acq_button.setText(_translate("AcquisitionTabWidget", "SINGLE"))
        self.clear_data_button.setText(_translate("AcquisitionTabWidget", "Clear DP5 Data"))

        self.minix_monitor_group.setTitle(_translate("AcquisitionTabWidget", "Mini-X Monitor"))
        self.label_minix_volt.setText(_translate("AcquisitionTabWidget", "Voltage (kV):"))
        self.minix_hv_monitor_display.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_minix_curr.setText(_translate("AcquisitionTabWidget", "Current (uA):"))
        self.minix_current_monitor_display.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_minix_temp.setText(_translate("AcquisitionTabWidget", "Board Temp (C):"))
        self.minix_board_temp_display.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_minix_power.setText(_translate("AcquisitionTabWidget", "Power (mW):"))
        self.minix_power_display.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_minix_status.setText(_translate("AcquisitionTabWidget", "Status:"))
        self.minix_status_line_edit.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.minix_hv_indicator_label.setText(_translate("AcquisitionTabWidget", "HV ON"))

        self.dp5_monitor_group.setTitle(_translate("AcquisitionTabWidget", "DP5 Monitor"))
        self.label_dp5_type.setText(_translate("AcquisitionTabWidget", "Device Type:"))
        self.dp5_device_type_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_sn.setText(_translate("AcquisitionTabWidget", "Serial Number:"))
        self.dp5_serial_number_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_fw.setText(_translate("AcquisitionTabWidget", "Firmware:"))
        self.dp5_firmware_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_fpga.setText(_translate("AcquisitionTabWidget", "FPGA:"))
        self.dp5_fpga_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_fast.setText(_translate("AcquisitionTabWidget", "Fast Count:"))
        self.dp5_fast_count_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_slow.setText(_translate("AcquisitionTabWidget", "Slow Count:"))
        self.dp5_slow_count_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_live.setText(_translate("AcquisitionTabWidget", "Live Time (s):"))
        self.dp5_live_time_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_real.setText(_translate("AcquisitionTabWidget", "Real Time (s):"))
        self.dp5_real_time_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_det_temp.setText(_translate("AcquisitionTabWidget", "Det Temp:"))
        self.dp5_det_temp_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_board_temp.setText(_translate("AcquisitionTabWidget", "Board Temp:"))
        self.dp5_board_temp_label.setText(_translate("AcquisitionTabWidget", "N/A"))
        self.label_dp5_hv.setText(_translate("AcquisitionTabWidget", "Det HV:"))
        self.dp5_hv_label.setText(_translate("AcquisitionTabWidget", "N/A"))

    # --- Helper method (moved from AcquisitionTabWidget) ---
    # This allows the Ui class to provide the method needed by the container widget
    def set_minix_hv_indicator(self, is_on):
        """Sets the visual state of the MiniX HV indicator LED."""
        if hasattr(self, 'minix_hv_indicator_led'):
             self.minix_hv_indicator_led.set_state(is_on)