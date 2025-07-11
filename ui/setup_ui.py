from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_SetupTab(object): # Inherit from object
    def setupUi(self, SetupTabWidget): # Accept the target widget instance
        SetupTabWidget.setObjectName("SetupTabWidget")
        # SetupTabWidget.resize(800, 600) # Example size, adjust as needed

        # --- Top Level Layout ---
        self.top_level_layout = QtWidgets.QVBoxLayout(SetupTabWidget) # Use SetupTabWidget here
        self.top_level_layout.setObjectName("top_level_layout")
        self.main_columns_layout = QtWidgets.QHBoxLayout()
        self.main_columns_layout.setObjectName("main_columns_layout")

        # --- Column Layouts ---
        self.minix_layout = QtWidgets.QVBoxLayout()
        self.minix_layout.setObjectName("minix_layout")
        self.dp5_layout = QtWidgets.QVBoxLayout()
        self.dp5_layout.setObjectName("dp5_layout")
        self.acq_setup_layout = QtWidgets.QVBoxLayout()
        self.acq_setup_layout.setObjectName("acq_setup_layout")

        # --- Column 1: Mini-X Setup ---
        self.minix_group = QtWidgets.QGroupBox(SetupTabWidget) # Parent is SetupTabWidget
        self.minix_group.setObjectName("minix_group")
        self.minix_group_layout = QtWidgets.QGridLayout(self.minix_group)
        self.minix_group_layout.setVerticalSpacing(15)
        self.minix_group_layout.setObjectName("minix_group_layout")

        self.minix_connect_button = QtWidgets.QPushButton(self.minix_group)
        self.minix_connect_button.setObjectName("minix_connect_button")
        self.minix_disconnect_button = QtWidgets.QPushButton(self.minix_group)
        self.minix_disconnect_button.setObjectName("minix_disconnect_button")
        minix_conn_btn_layout = QtWidgets.QHBoxLayout() # Layout for buttons
        minix_conn_btn_layout.addWidget(self.minix_connect_button)
        minix_conn_btn_layout.addWidget(self.minix_disconnect_button)
        self.minix_group_layout.addLayout(minix_conn_btn_layout, 0, 0, 1, 2) # Add layout to grid

        self.minix_hv_set_label = QtWidgets.QLabel(self.minix_group)
        self.minix_hv_set_label.setObjectName("minix_hv_set_label")
        self.minix_group_layout.addWidget(self.minix_hv_set_label, 1, 0, QtCore.Qt.AlignRight)

        self.minix_hv_set_input = QtWidgets.QLineEdit(self.minix_group)
        self.minix_hv_set_input.setObjectName("minix_hv_set_input")
        self.minix_group_layout.addWidget(self.minix_hv_set_input, 1, 1)

        self.minix_current_set_label = QtWidgets.QLabel(self.minix_group)
        self.minix_current_set_label.setObjectName("minix_current_set_label")
        self.minix_group_layout.addWidget(self.minix_current_set_label, 2, 0, QtCore.Qt.AlignRight)

        self.minix_current_set_input = QtWidgets.QLineEdit(self.minix_group)
        self.minix_current_set_input.setObjectName("minix_current_set_input")
        self.minix_group_layout.addWidget(self.minix_current_set_input, 2, 1)

        self.minix_set_hv_current_button = QtWidgets.QPushButton(self.minix_group)
        self.minix_set_hv_current_button.setObjectName("minix_set_hv_current_button")
        self.minix_group_layout.addWidget(self.minix_set_hv_current_button, 3, 0, 1, 2) # Span 2 columns

        self.minix_continuous_checkbox = QtWidgets.QCheckBox(self.minix_group)
        self.minix_continuous_checkbox.setObjectName("minix_continuous_checkbox")
        self.minix_group_layout.addWidget(self.minix_continuous_checkbox, 4, 0, 1, 2) # Span 2 columns

        # Spacer
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.minix_group_layout.addItem(spacerItem, 5, 0, 1, 2) # Span 2 columns

        self.minix_layout.addWidget(self.minix_group)
        self.main_columns_layout.addLayout(self.minix_layout, 33) # Add column layout to main columns

        # --- Column 2: DP-5 / X-123 Setup ---
        self.dp5_group = QtWidgets.QGroupBox(SetupTabWidget) # Parent is SetupTabWidget
        self.dp5_group.setObjectName("dp5_group")
        self.dp5_group_layout = QtWidgets.QGridLayout(self.dp5_group)
        self.dp5_group_layout.setVerticalSpacing(10)
        self.dp5_group_layout.setColumnStretch(0, 1) # Allow stretch
        self.dp5_group_layout.setObjectName("dp5_group_layout")

        self.dp5_connect_button = QtWidgets.QPushButton(self.dp5_group)
        self.dp5_connect_button.setObjectName("dp5_connect_button")
        self.dp5_disconnect_button = QtWidgets.QPushButton(self.dp5_group)
        self.dp5_disconnect_button.setObjectName("dp5_disconnect_button")
        dp5_conn_layout = QtWidgets.QHBoxLayout()
        dp5_conn_layout.addWidget(self.dp5_connect_button)
        dp5_conn_layout.addWidget(self.dp5_disconnect_button)
        self.dp5_group_layout.addLayout(dp5_conn_layout, 0, 0, 1, 2) # Span 2 cols

        self.dp5_load_config_button = QtWidgets.QPushButton(self.dp5_group)
        self.dp5_load_config_button.setObjectName("dp5_load_config_button")
        self.dp5_group_layout.addWidget(self.dp5_load_config_button, 1, 0, 1, 2) # Span 2 cols

        self.dp5_save_folder_label = QtWidgets.QLabel(self.dp5_group)
        self.dp5_save_folder_label.setObjectName("dp5_save_folder_label")
        self.dp5_group_layout.addWidget(self.dp5_save_folder_label, 2, 0, 1, 2) # Span 2 cols

        self.dp5_save_folder_display = QtWidgets.QLineEdit(self.dp5_group)
        self.dp5_save_folder_display.setReadOnly(True)
        self.dp5_save_folder_display.setObjectName("dp5_save_folder_display")
        self.dp5_group_layout.addWidget(self.dp5_save_folder_display, 3, 0, 1, 2) # Span 2 cols

        self.dp5_choose_save_folder_button = QtWidgets.QPushButton(self.dp5_group)
        self.dp5_choose_save_folder_button.setObjectName("dp5_choose_save_folder_button")
        self.dp5_group_layout.addWidget(self.dp5_choose_save_folder_button, 4, 0, 1, 2) # Span 2 cols

        # Spacer
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.dp5_group_layout.addItem(spacerItem1, 5, 0, 1, 2) # Span 2 cols

        self.dp5_layout.addWidget(self.dp5_group)
        self.main_columns_layout.addLayout(self.dp5_layout, 33) # Add column layout to main columns

        # --- Column 3: Acquisition Setup ---
        self.acq_setup_group = QtWidgets.QGroupBox(SetupTabWidget) # Parent is SetupTabWidget
        self.acq_setup_group.setObjectName("acq_setup_group")
        self.acq_setup_group_layout = QtWidgets.QGridLayout(self.acq_setup_group)
        self.acq_setup_group_layout.setVerticalSpacing(15)
        self.acq_setup_group_layout.setObjectName("acq_setup_group_layout")

        self.surface_width_label = QtWidgets.QLabel(self.acq_setup_group)
        self.surface_width_label.setObjectName("surface_width_label")
        self.acq_setup_group_layout.addWidget(self.surface_width_label, 0, 0)
        self.surface_width_input = QtWidgets.QLineEdit(self.acq_setup_group)
        self.surface_width_input.setObjectName("surface_width_input")
        self.acq_setup_group_layout.addWidget(self.surface_width_input, 0, 1)

        self.surface_height_label = QtWidgets.QLabel(self.acq_setup_group)
        self.surface_height_label.setObjectName("surface_height_label")
        self.acq_setup_group_layout.addWidget(self.surface_height_label, 1, 0)
        self.surface_height_input = QtWidgets.QLineEdit(self.acq_setup_group)
        self.surface_height_input.setObjectName("surface_height_input")
        self.acq_setup_group_layout.addWidget(self.surface_height_input, 1, 1)

        self.num_points_label = QtWidgets.QLabel(self.acq_setup_group)
        self.num_points_label.setObjectName("num_points_label")
        self.acq_setup_group_layout.addWidget(self.num_points_label, 2, 0)
        self.num_points_input = QtWidgets.QLineEdit(self.acq_setup_group)
        self.num_points_input.setObjectName("num_points_input")
        self.acq_setup_group_layout.addWidget(self.num_points_input, 2, 1)

        self.time_per_point_label = QtWidgets.QLabel(self.acq_setup_group)
        self.time_per_point_label.setObjectName("time_per_point_label")
        self.acq_setup_group_layout.addWidget(self.time_per_point_label, 3, 0)
        self.time_per_point_input = QtWidgets.QLineEdit(self.acq_setup_group)
        self.time_per_point_input.setObjectName("time_per_point_input")
        self.acq_setup_group_layout.addWidget(self.time_per_point_input, 3, 1)

        self.num_repetitions_label = QtWidgets.QLabel(self.acq_setup_group)
        self.num_repetitions_label.setObjectName("num_repetitions_label")
        self.acq_setup_group_layout.addWidget(self.num_repetitions_label, 4, 0)
        self.num_repetitions_input = QtWidgets.QLineEdit(self.acq_setup_group)
        self.num_repetitions_input.setObjectName("num_repetitions_input")
        self.acq_setup_group_layout.addWidget(self.num_repetitions_input, 4, 1)

        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.acq_setup_group_layout.addItem(spacerItem2, 5, 0, 1, 2)

        self.acq_setup_layout.addWidget(self.acq_setup_group)
        self.main_columns_layout.addLayout(self.acq_setup_layout, 33) # Add column layout to main columns

        # --- Add columns layout and stretch to top level ---
        self.top_level_layout.addLayout(self.main_columns_layout) # Add main columns
        # Add stretch if desired, maybe less needed if content fills space
        # spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.top_level_layout.addItem(spacerItem3)

        self.retranslateUi(SetupTabWidget) # Call retranslateUi
        QtCore.QMetaObject.connectSlotsByName(SetupTabWidget) # Needed if using slots by name

    def retranslateUi(self, SetupTabWidget):
        _translate = QtCore.QCoreApplication.translate
        SetupTabWidget.setWindowTitle(_translate("SetupTabWidget", "Form")) # Or remove if title set elsewhere

        # Column 1
        self.minix_group.setTitle(_translate("SetupTabWidget", "Mini-X Setup"))
        self.minix_connect_button.setText(_translate("SetupTabWidget", "Connect MiniX"))
        self.minix_disconnect_button.setText(_translate("SetupTabWidget", "Disconnect MiniX"))
        self.minix_hv_set_label.setText(_translate("SetupTabWidget", "Voltage Set:"))
        self.minix_hv_set_input.setPlaceholderText(_translate("SetupTabWidget", "kV (e.g., 10)"))
        self.minix_current_set_label.setText(_translate("SetupTabWidget", "Current Set:"))
        self.minix_current_set_input.setPlaceholderText(_translate("SetupTabWidget", "uA (e.g., 10)"))
        self.minix_set_hv_current_button.setText(_translate("SetupTabWidget", "Set High Voltage and Current"))
        self.minix_continuous_checkbox.setText(_translate("SetupTabWidget", "Keep MiniX HV ON during sequence?"))

        # Column 2
        self.dp5_group.setTitle(_translate("SetupTabWidget", "DP5 / X-123 Setup"))
        self.dp5_connect_button.setText(_translate("SetupTabWidget", "Connect DP5"))
        self.dp5_disconnect_button.setText(_translate("SetupTabWidget", "Disconnect DP5"))
        self.dp5_load_config_button.setText(_translate("SetupTabWidget", "Load DP5 Config File..."))
        self.dp5_save_folder_label.setText(_translate("SetupTabWidget", "Spectrum Save Folder:"))
        self.dp5_save_folder_display.setPlaceholderText(_translate("SetupTabWidget", "Select folder for saved spectra..."))
        self.dp5_choose_save_folder_button.setText(_translate("SetupTabWidget", "Choose Folder..."))

        # Column 3
        self.acq_setup_group.setTitle(_translate("SetupTabWidget", "Acquisition Parameters"))
        self.surface_width_label.setText(_translate("SetupTabWidget", "Surface Width:"))
        self.surface_height_label.setText(_translate("SetupTabWidget", "Surface Height:"))
        self.num_points_label.setText(_translate("SetupTabWidget", "Num Points (Mapping):"))
        self.time_per_point_label.setText(_translate("SetupTabWidget", "Acquisition Duration (s):"))
        self.num_repetitions_label.setText(_translate("SetupTabWidget", "Number of Repetitions:"))
        self.num_repetitions_input.setPlaceholderText(_translate("SetupTabWidget", "e.g., 10"))
        self.time_per_point_input.setPlaceholderText(_translate("SetupTabWidget", "e.g., 60"))