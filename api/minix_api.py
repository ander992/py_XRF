import os
import sys
import enum
import time
import ctypes
import struct

# --- Configuration ---
# IMPORTANT: Ensure you are running this script with a 32-BIT PYTHON INTERPRETER!
if struct.calcsize('P') * 8 != 32:
    raise RuntimeError(
        "FATAL: This application requires a 32-bit Python interpreter."
    )

# --- Load the DLL ---
# IMPORTANT: Place MiniX.dll in the same directory as this script,
# or provide the full, correct path to the DLL.
DLL_NAME = "MiniX.dll"
_dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DLL_NAME)
_minix_lib = None

if not os.path.exists(_dll_path): print(f"FATAL: DLL not found: {_dll_path}"); sys.exit(1)

try:
    # Try loading from the script's directory first
    if os.path.exists(_dll_path):
        _minix_lib = ctypes.windll.LoadLibrary(_dll_path)
        print(f"Successfully loaded {DLL_NAME} from {_dll_path}")
    else:
        # If not found locally, try loading from system PATH
        _minix_lib = ctypes.windll.LoadLibrary(DLL_NAME)
        print(f"Successfully loaded {DLL_NAME} from system PATH.")

except FileNotFoundError:
     raise FileNotFoundError(
        f"Error: {DLL_NAME} not found at '{_dll_path}' or in system PATH. "
        "Please place the 32-bit DLL in the same directory as this script "
        "or ensure it's in the system PATH."
    ); sys.exit(1)
except OSError as e: print(f"FATAL: Error loading {_dll_path}: {e}"); sys.exit(1)
except Exception as e: print(f"FATAL: Unexpected error loading {_dll_path}: {e}"); sys.exit(1)



# --- Custom Exception Class ---
class MiniXAPIError(Exception):
    """ Base exception for Mini-X API related errors. """
    pass

class ControllerNotRunningError(MiniXAPIError):
    """ Raised when an operation requires the controller but it's not running. """
    pass

class APICommandError(MiniXAPIError):
    """ Raised when an API command fails or returns an error state. """
    pass

class StatusError(MiniXAPIError):
    """ Raised for specific error status codes reported by the device. """
    pass



# --- Enumerations ---
# Using IntFlag for easier bitmask operations
class MiniXCommands(enum.IntFlag): 
    """
    Commands for SendMiniXCommand and masks for mxmEnabledCmds.
    From MiniXAPI.h and Programming Guide.
    NOTE: mxcDisabled should NOT be sent via SendMiniXCommand.
    """
    mxcDisabled = 0
    mxcStartMiniX = 1       # start minix controller
    mxcHVOn = 2             # turn high voltage on
    mxcHVOff = 4            # turn high voltage off
    mxcSetHVandCurrent = 8  # set high voltage and current
    mxcExit = 16            # exit controller

class MiniXStatus(enum.IntEnum):
    """
    Mini-X Controller Status Codes (used in mxmStatusInd).
    From MiniXAPI.h and Programming Guide[cite: 1].
    """
    mxstNoStatus = 0                        # no status available 
    mxstDriversNotLoaded = 1                # drivers were not found, install drivers 
    mxstMiniXApplicationReady = 2           # application is ready to connect to minix 
    mxstPortCLOSED = 3                      # minix detected, port closed, will attempt connect 
    mxstNoDevicesAttached = 4               # minix is not connected or is not powered 
    mxstMiniXControllerSelected = 5         # minix has been found
    mxstMiniXControllerReady = 6            # minix connected and ready for first command 
    mxstMiniXControllerFailedToOpen = 7     # minix detected, but failed to open
    mxstNoDeviceSelected = 8                # could not select minix device
    mxstRequestedVoltageOutOfRange = 9      # hv was selected out of range,api will set in range
    mxstRequestedCurrentOutOfRange = 10     # uA was selected out of range,api will set in range
    mxstConnectingToMiniX = 11              # api busy attempting to connect to minix
    mxstUpdatingSettings = 12               # api busy updating settings
    mxstMiniXReady = 13                     # ready for next operation



# --- Data Structures based on the guide ---
class MiniX_Monitor(ctypes.Structure):
    """
    Holds monitored values from ReadMiniXMonitor.
    """
    _fields_ = [
        ("mxmHighVoltage_kV", ctypes.c_double),   # Monitored HV
        ("mxmCurrent_uA", ctypes.c_double),       # Monitored Current
        ("mxmPower_mW", ctypes.c_double),         # Calculated Power (mW)
        ("mxmTemperatureC", ctypes.c_double),     # Board Temperature (C)
        ("mxmRefreshed", ctypes.c_ubyte),      # Monitor data refresh OK (1=True, 0=False)
        ("mxmInterLock", ctypes.c_ubyte),      # Hardware Interlock (0=Open, 1=Closed/Restored)
        ("mxmEnabledCmds", ctypes.c_ubyte),    # Bitmask of enabled commands (MiniXCommands)
        ("mxmStatusInd", ctypes.c_ubyte),      # Status indicator code (MiniXStatus)
        ("mxmOutOfRange", ctypes.c_ubyte),     # Wattage value out of range (1=True, 0=False)
        ("mxmHVOn", ctypes.c_ubyte),           # High voltage on indicator (1=True, 0=False)
        ("mxmReserved", ctypes.c_double)       # Reserved, should be 123.456
    ]

    def __str__(self):
        """ Provides a string representation of the monitor data. """
        status_str = get_status_string(self.mxmStatusInd)
        hv_on_str = "ON" if self.mxmHVOn else "OFF"
        interlock_str = "CLOSED" if self.mxmInterLock else "OPEN"
        enabled_cmds = ", ".join(cmd.name for cmd in MiniXCommands if self.mxmEnabledCmds & cmd.value and cmd.value != 0) or "None"
        return (
            f"MiniX_Monitor(\n"
            f"  HV={self.mxmHighVoltage_kV:.2f}kV, Current={self.mxmCurrent_uA:.1f}uA, "
            f"Power={self.mxmPower_mW:.1f}mW, Temp={self.mxmTemperatureC:.1f}C\n"
            f"  HV_Status={hv_on_str}, Interlock={interlock_str}, "
            f"Status='{status_str}' ({self.mxmStatusInd})\n"
            f"  Refreshed={bool(self.mxmRefreshed)}, OutOfRange={bool(self.mxmOutOfRange)}, "
            f"EnabledCmds=[{enabled_cmds}] ({self.mxmEnabledCmds})\n"
            f")"
        )

class MiniX_Settings(ctypes.Structure):
    """
    Holds actual requested values set (after potential correction).
    """
    _fields_ = [
        ("HighVoltage_kV", ctypes.c_double),    # Actual HV setting
        ("Current_uA", ctypes.c_double)         # Actual Current setting
    ]

    def __str__(self):
        """ Provides a string representation of the settings data. """
        return (f"MiniX_Settings(HV={self.HighVoltage_kV:.2f}kV, "
                f"Current={self.Current_uA:.1f}uA)")

# --- Define Function Signatures ---
try:
    # void WINAPI OpenMiniX();
    _OpenMiniX = _minix_lib.OpenMiniX
    _OpenMiniX.argtypes = []
    _OpenMiniX.restype = None

    # byte WINAPI isMiniXDlg(); - Returns 1 (True) if open, 0 (False) otherwise
    _isMiniXDlg = _minix_lib.isMiniXDlg
    _isMiniXDlg.argtypes = []
    _isMiniXDlg.restype = ctypes.c_ubyte # Using ubyte for boolean byte

    # void WINAPI CloseMiniX();
    _CloseMiniX = _minix_lib.CloseMiniX
    _CloseMiniX.argtypes = []
    _CloseMiniX.restype = None

    # void WINAPI ReadMiniXMonitor(MiniX_Monitor *MiniXMonitor);
    _ReadMiniXMonitor = _minix_lib.ReadMiniXMonitor
    _ReadMiniXMonitor.argtypes = [ctypes.POINTER(MiniX_Monitor)]
    _ReadMiniXMonitor.restype = None

    # long WINAPI ReadMiniXSerialNumber();
    _ReadMiniXSerialNumber = _minix_lib.ReadMiniXSerialNumber
    _ReadMiniXSerialNumber.argtypes = []
    _ReadMiniXSerialNumber.restype = ctypes.c_long

    # void WINAPI ReadMiniXSettings(MiniX_Settings *MiniXSettings);
    _ReadMiniXSettings = _minix_lib.ReadMiniXSettings
    _ReadMiniXSettings.argtypes = [ctypes.POINTER(MiniX_Settings)]
    _ReadMiniXSettings.restype = None

    # long WINAPI ReadMinixOemMxDeviceType();
    _ReadMinixOemMxDeviceType = _minix_lib.ReadMinixOemMxDeviceType
    _ReadMinixOemMxDeviceType.argtypes = []
    _ReadMinixOemMxDeviceType.restype = ctypes.c_long

    # void WINAPI SendMiniXCommand(byte MiniXCommand);
    _SendMiniXCommand = _minix_lib.SendMiniXCommand
    _SendMiniXCommand.argtypes = [ctypes.c_ubyte] # Command code from MiniXCommands enum
    _SendMiniXCommand.restype = None

    # void WINAPI SetMiniXHV(double HighVoltage_kV);
    _SetMiniXHV = _minix_lib.SetMiniXHV
    _SetMiniXHV.argtypes = [ctypes.c_double]
    _SetMiniXHV.restype = None

    # void WINAPI SetMiniXCurrent(double Current_uA);
    _SetMiniXCurrent = _minix_lib.SetMiniXCurrent
    _SetMiniXCurrent.argtypes = [ctypes.c_double]
    _SetMiniXCurrent.restype = None

except AttributeError as e:
    raise MiniXAPIError(
        f"FATAL Error: Function not found in {DLL_NAME}. "
        f"Check DLL version/integrity. Error: {e}"
    )

# --- Helper Functions / Convenience Wrappers ---

def is_controller_running() -> bool:
    """
    Checks if the non-visible Mini-X Controller Application instance exists. Calls isMiniXDlg.
    Returns:
        bool: True if the controller application is running, False otherwise.
    """
    return bool(_isMiniXDlg())

def start_controller_application(wait_time: float = 1.0, attempts: int = 3):
    """
    Opens an instance of the non-visible Mini-X Controller Application.
    Calls OpenMiniX. Waits briefly and checks if it started.
    Args:
        wait_time (float): Time in seconds to wait between attempts.
        attempts (int): Number of attempts to check if controller started.
    Raises:
        ControllerNotRunningError: If the controller application fails to start after specified attempts.
    """
    if not is_controller_running():
        print("Starting Mini-X Controller Application...")
        _OpenMiniX()
        # Wait and verify it started
        for attempt in range(attempts):
            time.sleep(wait_time)
            if is_controller_running():
                print("Controller application started successfully.")
                # Check initial status
                status = get_monitor_data()
                if status and status.mxmStatusInd == MiniXStatus.mxstMiniXApplicationReady:
                    print("Controller status: mxstMiniXApplicationReady.")
                elif status:
                    print(f"Initial controller status: {get_status_string(status.mxmStatusInd)}")
                else:
                     print("Could not get initial controller status.")
                return
            print(f"Waiting for controller application to start (attempt {attempt + 1}/{attempts})...")
        raise ControllerNotRunningError("Failed to start the Mini-X Controller Application.")
    else:
        print("Controller application is already running.")

def close_controller_application():
    """
    Closes the instance of the Mini-X Controller Application. Calls CloseMiniX.
    """
    if is_controller_running():
        print("Closing Mini-X Controller Application...")
        _CloseMiniX()
        time.sleep(0.5)
        if not is_controller_running():
            print("Controller application closed successfully.")
        else:
            print("Warning: Controller application did not seem to close as expected.")
    else:
        print("Controller application not running, nothing to close.")

def get_monitor_data(raise_on_unrefreshed: bool = False) -> MiniX_Monitor:
    """
    Reads the latest monitor/status data from the controller. Calls ReadMiniXMonitor.
    Args:
        raise_on_unrefreshed (bool): If True, raises APICommandError if the monitor data wasn't refreshed. 
        Otherwise, returns potentially stale data.

    Returns:
        MiniX_Monitor: An object containing the monitor data.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
        APICommandError: If raise_on_unrefreshed is True and data wasn't refreshed.
    """
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot read monitor data, controller not running.")

    monitor_data = MiniX_Monitor()
    _ReadMiniXMonitor(ctypes.byref(monitor_data))

    if not monitor_data.mxmRefreshed:
        msg = "Monitor data was not refreshed (controller busy or communication issue?)."
        if raise_on_unrefreshed:
            raise APICommandError(msg)
        else:
            print(f"Warning: {msg} Returning potentially stale data.")

    # Check for specific error statuses reported by the device itself
    status_enum = MiniXStatus(monitor_data.mxmStatusInd)
    if status_enum in [MiniXStatus.mxstDriversNotLoaded,
                       MiniXStatus.mxstMiniXControllerFailedToOpen,
                       MiniXStatus.mxstNoDeviceSelected,
                       MiniXStatus.mxstNoDevicesAttached]:
        # Raise a specific error for critical statuses found during monitoring
        raise StatusError(f"Device reported error status: {get_status_string(status_enum)}")

    return monitor_data

def get_current_settings() -> MiniX_Settings:
    """
    Reads the actual HV and Current settings stored in the controller app.
    Calls ReadMiniXSettings.

    Returns:
        MiniX_Settings: An object containing the actual settings.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
    """
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot read settings, controller not running.")

    settings_data = MiniX_Settings()
    _ReadMiniXSettings(ctypes.byref(settings_data))
    return settings_data

def get_serial_number() -> int:
    """
    Reads the Mini-X serial number.
    Calls ReadMiniXSerialNumber.

    Returns:
        int: The serial number.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
    """
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot read serial number, controller not running.")
    return _ReadMiniXSerialNumber()

def get_device_type() -> int:
    """
    Reads the Mini-X device type indicator.
    Calls ReadMinixOemMxDeviceType.
    Refer to guide Table 6.1 for interpretation.

    Returns:
        int: The device type code.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
    """
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot read device type, controller not running.")
    return _ReadMinixOemMxDeviceType()

def send_command(command: MiniXCommands, check_enabled: bool = True):
    """
    Sends a control command to the Mini-X controller.
    Calls SendMiniXCommand.

    Args:
        command (MiniXCommands): The command to send (from the enum).
        check_enabled (bool): If True, checks if the command is enabled in the
                              current monitor status before sending (recommended).
                              Does not check for mxcExit as it's always allowed.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
        TypeError: If the command is not a valid MiniXCommands enum member.
        APICommandError: If check_enabled is True and the command is not currently
                         enabled according to the monitor status.
        ValueError: If attempting to send mxcDisabled.
    """
    if not isinstance(command, MiniXCommands):
        raise TypeError("Invalid command type. Use MiniXCommands enum.")
    if command == MiniXCommands.mxcDisabled:
         raise ValueError("mxcDisabled command should not be sent.")

    if not is_controller_running():
        raise ControllerNotRunningError(f"Cannot send command {command.name}, controller not running.")

    if check_enabled and command != MiniXCommands.mxcExit:
        monitor_data = get_monitor_data() # Get current status
        if not (monitor_data.mxmEnabledCmds & command.value):
            enabled_cmds = ", ".join(cmd.name for cmd in MiniXCommands if monitor_data.mxmEnabledCmds & cmd.value and cmd.value != 0) or "None"
            raise APICommandError(
                f"Command {command.name} is not enabled. "
                f"Current enabled commands: [{enabled_cmds}]"
            )

    print(f"Sending command: {command.name}")
    _SendMiniXCommand(command.value)
    time.sleep(0.1)

def set_voltage(voltage_kv: float):
    """
    Sets the requested high voltage (kV). Actual value may be corrected by API[cite: 143].
    Calls SetMiniXHV[cite: 146]. Use get_current_settings() to verify actual value.

    Args:
        voltage_kv (float): The requested voltage in kilovolts.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
        TypeError: If voltage_kv is not a number.
    """
    if not isinstance(voltage_kv, (int, float)):
        raise TypeError("Voltage must be a number (int or float).")
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot set voltage, controller not running.")

    print(f"Requesting HV set to: {float(voltage_kv):.2f} kV")
    _SetMiniXHV(ctypes.c_double(voltage_kv))
    # Check status for out-of-range indication if needed immediately
    status = get_monitor_data()
    if status.mxmStatusInd == MiniXStatus.mxstRequestedVoltageOutOfRange:
        print("Warning: Requested voltage was out of range, API corrected.")

def set_current(current_ua: float):
    """
    Sets the requested current (uA). Actual value may be corrected by API[cite: 150].
    Calls SetMiniXCurrent[cite: 153]. Use get_current_settings() to verify actual value.

    Args:
        current_ua (float): The requested current in microamps.

    Raises:
        ControllerNotRunningError: If the controller application is not running.
        TypeError: If current_ua is not a number.
    """
    if not isinstance(current_ua, (int, float)):
        raise TypeError("Current must be a number (int or float).")
    if not is_controller_running():
        raise ControllerNotRunningError("Cannot set current, controller not running.")

    print(f"Requesting Current set to: {float(current_ua):.2f} uA")
    _SetMiniXCurrent(ctypes.c_double(current_ua))
    # Check status for out-of-range indication if needed immediately
    status = get_monitor_data()
    if status.mxmStatusInd == MiniXStatus.mxstRequestedCurrentOutOfRange:
        print("Warning: Requested current was out of range, API corrected.")

def get_status_string(status_code: int) -> str:
    """
    Helper to get a descriptive string for a MiniXStatus code.
    Uses the names from the MiniXStatus enum.
    """
    try:
        return MiniXStatus(status_code).name
    except ValueError:
        return f"UnknownStatusCode_{status_code}"