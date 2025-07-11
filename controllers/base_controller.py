# controllers/base_controller.py
# Base class for device controller logic

from PyQt5.QtCore import QObject, pyqtSignal

class BaseController(QObject):
    """
    Base class for device controllers (DP5, MiniX).
    Provides common structure for state management and signaling.
    """
    # --- Common Signals ---
    # Emitted when the connection status changes
    connection_changed = pyqtSignal(bool)
    # Emitted when an error occurs during an operation
    error_occurred = pyqtSignal(str)
    # Emitted to provide general status updates/messages to the UI
    status_message = pyqtSignal(str)

    def __init__(self, api_module=None, parent=None):
        """
        Initialize the base controller.

        Args:
            api_module: Reference to the specific device API module (e.g., dp5_api).
                        Can be None if API is loaded dynamically or not always needed.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._api = api_module
        self._is_connected = False
        self._last_error = ""

    # --- Common Properties ---
    @property
    def is_connected(self):
        """Returns the current connection status."""
        return self._is_connected

    @property
    def last_error(self):
        """Returns the last reported error message."""
        return self._last_error

    # --- Common Methods (Protected) ---
    def _set_connected(self, connected_state: bool):
        """
        Protected method to update connection state and emit signal if changed.
        Should be called by subclasses after successful connect/disconnect.
        """
        if self._is_connected != connected_state:
            self._is_connected = connected_state
            self.connection_changed.emit(self._is_connected)

    def _report_error(self, message: str):
        """
        Protected method for subclasses to report errors.
        Stores the error and emits the error_occurred signal.
        """
        print(f"ERROR: {message}")
        self._last_error = message
        self.error_occurred.emit(message)

    def _post_status_message(self, message: str):
        """
        Protected method for subclasses to send informational messages to the UI.
        """
        print(f"STATUS: {message}")
        self.status_message.emit(message)
