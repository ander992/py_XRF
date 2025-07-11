# Updated api/dp5_api.py
# Populated with all function prototypes from DP5 API DLL Functions.pdf

import os
import sys
import enum
import time
import ctypes
import struct
import numpy as np # Import numpy for array manipulation

# --- Configuration ---
# IMPORTANT: Ensure you are running this script with a 32-BIT PYTHON INTERPRETER!
if struct.calcsize('P') * 8 != 32:
    raise RuntimeError(
        "FATAL: This application requires a 32-bit Python interpreter."
    )

# --- Load the DLL ---
# IMPORTANT: Place dp5api.dll and libusb.dll in the same directory as this script,
# or provide the full, correct path to the DLL.
DLL_NAME = "dp5api.dll"
_dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DLL_NAME)
_libusb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libusb.dll")
_dp5_lib = None

# Ensure libusb.dll is loaded first if needed, or handled by the OS/dp5api.dll implicitly
# No explicit load needed here unless specified by Amptek documentation

if not os.path.exists(_dll_path): print(f"FATAL: DLL not found: {_dll_path}"); sys.exit(1)
if not os.path.exists(_libusb_path): print(f"WARNING: libusb.dll not found: {_libusb_path}. DP5 API might fail if it's required."); # Changed to warning

try:
    if os.path.exists(_dll_path):
        _dp5_lib = ctypes.windll.LoadLibrary(_dll_path)
        print(f"Successfully loaded {DLL_NAME} from {_dll_path}")
    else:
        # This branch might be less reliable if the DLL isn't in the PATH
        _dp5_lib = ctypes.windll.LoadLibrary(DLL_NAME)
        print(f"Successfully loaded {DLL_NAME} from system PATH.")

except FileNotFoundError: raise FileNotFoundError(
        f"Error: {DLL_NAME} not found at '{_dll_path}' or in system PATH. "
        "Please place the 32-bit DLL in the same directory as this script "
        "or ensure it's in the system PATH."
        ); sys.exit(1)
except OSError as e: print(f"FATAL: Error loading {_dll_path}: {e}"); sys.exit(1)
except Exception as e: print(f"FATAL: Unexpected error loading {_dll_path}: {e}"); sys.exit(1)


# --- Constants (from Data Size Guide PDF [cite: 31]) ---
MAX_BUFFER_DATA = 8192
MAX_SCOPE_DATA = 2048
MAX_CONFIGURATION_SIZE = 2048
MAX_STATUS_SIZE = 1024
MAX_DESCRIPTION_SIZE = 128
MAX_TAG_SIZE = 16
MAX_START_TIME = 40
MAX_FILENAME_LEN = 256 # [cite: 32]
MAX_DTS_LEN = 20 # [cite: 32] Date Time Stamp len for GetStartTime

# --- Type Definitions ---
# Using c_ubyte for BOOL as seen in minix_api.py and existing dp5_api.py
BOOL_TYPE = ctypes.c_ubyte

# --- Structures ---

# --- Status Packet Structure (from existing dp5_api.py, appears consistent with Programmer's Guide)
class DP5_DP4_FORMAT_STATUS(ctypes.Structure):
    _fields_ = [
        ("RAW", ctypes.c_ubyte * 64), ("SerialNumber", ctypes.c_ulong),
        ("FastCount", ctypes.c_double), ("SlowCount", ctypes.c_double),
        ("FPGA", ctypes.c_ubyte), ("Firmware", ctypes.c_ubyte),
        ("Build", ctypes.c_ubyte), ("AccumulationTime", ctypes.c_double),
        ("RealTime", ctypes.c_double), ("LiveTime", ctypes.c_double),
        ("HV", ctypes.c_double), ("DET_TEMP", ctypes.c_double),
        ("DP5_TEMP", ctypes.c_double), ("PX4", BOOL_TYPE),
        ("AFAST_LOCKED", BOOL_TYPE), ("MCA_EN", BOOL_TYPE),
        ("PRECNT_REACHED", BOOL_TYPE), ("PresetRtDone", BOOL_TYPE),
        ("PresetLtDone", BOOL_TYPE), ("SUPPLIES_ON", BOOL_TYPE),
        ("SCOPE_DR", BOOL_TYPE), ("DP5_CONFIGURED", BOOL_TYPE),
        ("GP_COUNTER", ctypes.c_double), ("AOFFSET_LOCKED", BOOL_TYPE),
        ("MCS_DONE", BOOL_TYPE), ("RAM_TEST_RUN", BOOL_TYPE),
        ("RAM_TEST_ERROR", BOOL_TYPE), ("DCAL", ctypes.c_double),
        ("PZCORR", ctypes.c_ubyte), ("UC_TEMP_OFFSET", ctypes.c_ubyte),
        ("AN_IN", ctypes.c_double), ("VREF_IN", ctypes.c_double),
        ("PC5_SN", ctypes.c_ulong), ("PC5_PRESENT", BOOL_TYPE),
        ("PC5_HV_POL", BOOL_TYPE), ("PC5_8_5V", BOOL_TYPE),
        ("ADC_GAIN_CAL", ctypes.c_double), ("ADC_OFFSET_CAL", ctypes.c_ubyte),
        ("SPECTRUM_OFFSET", ctypes.c_long), ("b80MHzMode", BOOL_TYPE),
        ("bFPGAAutoClock", BOOL_TYPE), ("DEVICE_ID", ctypes.c_ubyte),
        ("ReBootFlag", BOOL_TYPE), ("DPP_options", ctypes.c_ubyte),
        ("HPGe_HV_INH", BOOL_TYPE), ("HPGe_HV_INH_POL", BOOL_TYPE),
        ("TEC_Voltage", ctypes.c_double), ("DPP_ECO", ctypes.c_ubyte),
        ("AU34_2", BOOL_TYPE), ("isAscInstalled", BOOL_TYPE),
        ("isAscEnabled", BOOL_TYPE), ("bScintHas80MHzOption", BOOL_TYPE),
    ]

# --- Spectrum Structure (from existing dp5_api.py)
class Spec(ctypes.Structure):
     _fields_ = [
        ("DATA", ctypes.c_long * MAX_BUFFER_DATA), # Use c_long for 32-bit compatibility
        ("CHANNELS", ctypes.c_short),
    ]

# --- Spectrum (MCA) File Structure (from existing dp5_api.py)
class SpecFile(ctypes.Structure):
     _fields_ = [
        ("strTag", ctypes.c_char * MAX_TAG_SIZE),
        ("strDescription", ctypes.c_char * MAX_DESCRIPTION_SIZE),
        ("strSpectrumConfig", ctypes.c_char * MAX_CONFIGURATION_SIZE),
        ("strSpectrumStatus", ctypes.c_char * MAX_STATUS_SIZE),
        ("strStartTime", ctypes.c_char * MAX_START_TIME),
        ("AccumulationTime", ctypes.c_double),
        ("RealTime", ctypes.c_double),
        ("SerialNumber", ctypes.c_ulong),
    ]


# --- Define Function Prototypes ---
# Initialize all function wrappers to None first
( ConnectToDefaultDPP, ConnectToDPP, ConnectToDPPIndex, CloseConnection, CountDppDevices,
  ClearData, EnableMCA, DisableMCA, RequestSpectrumData, AcquireSpectrum, ConsoleSpectrum,
  GetDppStatus, DppStatusToString, DppStatusToStruct, GetDppSerialNumber,
  ReadDppConfigurationFromHardware, DppHwConfigToString, PresetModeToString,
  SendCommandString, SendConfigFileToDpp, SendScaToDpp, ShortenCfgCmds, DisplayPresets,
  ReadConfigFile, GetStartTime, SaveMCADataToFile, SetDisplayCfg, SetDisplayDebugInfo,
  SetDisplaySpectrum ) = (None,) * 29

# Define prototypes within a try block for robustness
try:
    # --- 1. USB Communications [cite: 35] ---
    # 1.1 ConnectToDefaultDPP [cite: 35]
    ConnectToDefaultDPP = _dp5_lib.ConnectToDefaultDPP
    ConnectToDefaultDPP.argtypes = []
    ConnectToDefaultDPP.restype = BOOL_TYPE

    # 1.2 ConnectToDPP [cite: 36]
    ConnectToDPP = _dp5_lib.ConnectToDPP
    ConnectToDPP.argtypes = [ctypes.c_long] # ISerialNumber [cite: 37]
    ConnectToDPP.restype = BOOL_TYPE

    # 1.3 ConnectToDPPIndex [cite: 38]
    ConnectToDPPIndex = _dp5_lib.ConnectToDPPIndex
    ConnectToDPPIndex.argtypes = [ctypes.c_int] # idxIndex [cite: 39]
    ConnectToDPPIndex.restype = BOOL_TYPE

    # 1.4 CloseConnection [cite: 41]
    CloseConnection = _dp5_lib.CloseConnection
    CloseConnection.argtypes = []
    CloseConnection.restype = None # void

    # 1.5 CountDppDevices [cite: 41]
    CountDppDevices = _dp5_lib.CountDppDevices
    CountDppDevices.argtypes = []
    CountDppDevices.restype = ctypes.c_int # Returns number of devices [cite: 42]

    # --- 2. Acquisition Control Functions [cite: 43] ---
    # 2.1 ClearData [cite: 43]
    ClearData = _dp5_lib.ClearData
    ClearData.argtypes = []
    ClearData.restype = None # void

    # 2.2 EnableMCA [cite: 43]
    EnableMCA = _dp5_lib.EnableMCA
    EnableMCA.argtypes = []
    EnableMCA.restype = None # void

    # 2.3 DisableMCA [cite: 44]
    DisableMCA = _dp5_lib.DisableMCA
    DisableMCA.argtypes = []
    DisableMCA.restype = None # void

    # 2.4 RequestSpectrumData [cite: 45]
    RequestSpectrumData = _dp5_lib.RequestSpectrumData
    RequestSpectrumData.argtypes = [ctypes.POINTER(Spec), ctypes.POINTER(DP5_DP4_FORMAT_STATUS)]
    RequestSpectrumData.restype = None # void

    # 2.5 AcquireSpectrum [cite: 46]
    AcquireSpectrum = _dp5_lib.AcquireSpectrum
    AcquireSpectrum.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_int] # dblPreset, dblDelay, iRefreshMS [cite: 47, 48]
    AcquireSpectrum.restype = None # void

    # 2.6 ConsoleSpectrum [cite: 50]
    ConsoleSpectrum = _dp5_lib.ConsoleSpectrum
    ConsoleSpectrum.argtypes = [ctypes.POINTER(Spec), ctypes.c_char_p] # SpectrumOut, sDppStatusString [cite: 51]
    ConsoleSpectrum.restype = None # void

    # --- 3. Status Functions [cite: 52] ---
    # 3.1 GetDppStatus [cite: 52]
    GetDppStatus = _dp5_lib.GetDppStatus
    GetDppStatus.argtypes = []
    GetDppStatus.restype = None # void

    # 3.2 DppStatusToString [cite: 55]
    DppStatusToString = _dp5_lib.DppStatusToString
    DppStatusToString.argtypes = [ctypes.c_char_p] # sDppStatusString [cite: 55]
    DppStatusToString.restype = None # void

    # 3.3 DppStatusToStruct [cite: 57]
    DppStatusToStruct = _dp5_lib.DppStatusToStruct
    DppStatusToStruct.argtypes = [ctypes.POINTER(DP5_DP4_FORMAT_STATUS)] # m_DP5_StatusOut [cite: 57]
    DppStatusToStruct.restype = None # void

    # 3.4 GetDppSerialNumber [cite: 58]
    GetDppSerialNumber = _dp5_lib.GetDppSerialNumber
    GetDppSerialNumber.argtypes = []
    GetDppSerialNumber.restype = ctypes.c_long # Returns serial number or 0 [cite: 59]

    # --- 4. Configuration Functions [cite: 61] ---
    # 4.1 ReadDppConfigurationFromHardware [cite: 61]
    ReadDppConfigurationFromHardware = _dp5_lib.ReadDppConfigurationFromHardware
    ReadDppConfigurationFromHardware.argtypes = []
    ReadDppConfigurationFromHardware.restype = None # void

    # 4.2 DppHwConfigToString [cite: 63]
    DppHwConfigToString = _dp5_lib.DppHwConfigToString
    DppHwConfigToString.argtypes = [BOOL_TYPE, ctypes.c_char_p] # bAddComments, strConfigOut [cite: 63]
    DppHwConfigToString.restype = ctypes.c_int # Returns size of output string or 0 [cite: 64]

    # 4.3 PresetModeToString [cite: 65]
    PresetModeToString = _dp5_lib.PresetModeToString
    PresetModeToString.argtypes = [ctypes.c_char_p] # strPresetModeOut [cite: 65]
    PresetModeToString.restype = None # void

    # 4.4 SendCommandString [cite: 68]
    SendCommandString = _dp5_lib.SendCommandString
    SendCommandString.argtypes = [ctypes.c_char_p] # strCMD [cite: 68]
    SendCommandString.restype = BOOL_TYPE

    # 4.5 SendConfigFileToDpp [cite: 69]
    SendConfigFileToDpp = _dp5_lib.SendConfigFileToDpp
    SendConfigFileToDpp.argtypes = [ctypes.c_char_p] # strFilename [cite: 70]
    SendConfigFileToDpp.restype = BOOL_TYPE

    # 4.6 SendScaToDpp [cite: 71]
    SendScaToDpp = _dp5_lib.SendScaToDpp
    SendScaToDpp.argtypes = [ctypes.c_char_p] # strFilename [cite: 71]
    SendScaToDpp.restype = BOOL_TYPE

    # 4.7 ShortenCfgCmds [cite: 72]
    ShortenCfgCmds = _dp5_lib.ShortenCfgCmds
    ShortenCfgCmds.argtypes = [ctypes.c_char_p, ctypes.c_char_p] # strCfgIn, strCfgOut [cite: 73]
    ShortenCfgCmds.restype = ctypes.c_int # Returns size of output string or 0

    # 4.8 DisplayPresets [cite: 76]
    DisplayPresets = _dp5_lib.DisplayPresets
    DisplayPresets.argtypes = []
    DisplayPresets.restype = None # void

    # 4.9 ReadConfigFile [cite: 77]
    ReadConfigFile = _dp5_lib.ReadConfigFile
    ReadConfigFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p] # strFilename, strCfgOut, strSplitCfgOut [cite: 77, 78]
    ReadConfigFile.restype = ctypes.c_int # Returns total size of ASCII config string [cite: 79]

    # --- 5. Spectrum File Functions [cite: 83] ---
    # 5.1 GetStartTime [cite: 84]
    GetStartTime = _dp5_lib.GetStartTime
    GetStartTime.argtypes = [ctypes.c_char * MAX_START_TIME, ctypes.c_char * MAX_DTS_LEN] # StartTime[], strDTS[] [cite: 84] - Use fixed char arrays
    GetStartTime.restype = ctypes.c_int # Docs don't specify return, assume int based on similar funcs or 0/-1 for error

    # 5.2 SaveMCADataToFile [cite: 86]
    SaveMCADataToFile = _dp5_lib.SaveMCADataToFile
    SaveMCADataToFile.argtypes = [ctypes.c_char_p, ctypes.POINTER(Spec), ctypes.POINTER(SpecFile)] # strFilename, SPECTRUM, sfInfo [cite: 86, 87]
    SaveMCADataToFile.restype = None # void

    # --- 6. Diagnostics [cite: 88] ---
    # 6.1 SetDisplayCfg [cite: 88]
    SetDisplayCfg = _dp5_lib.SetDisplayCfg
    SetDisplayCfg.argtypes = [BOOL_TYPE] # bShowConsoleCfg [cite: 88]
    SetDisplayCfg.restype = None # void

    # 6.2 SetDisplayDebugInfo [cite: 89]
    SetDisplayDebugInfo = _dp5_lib.SetDisplayDebugInfo
    SetDisplayDebugInfo.argtypes = [BOOL_TYPE] # bShowConsoleDebug [cite: 89]
    SetDisplayDebugInfo.restype = None # void

    # 6.3 SetDisplaySpectrum [cite: 90]
    SetDisplaySpectrum = _dp5_lib.SetDisplaySpectrum
    SetDisplaySpectrum.argtypes = [BOOL_TYPE] # bShowConsoleSpectrum [cite: 90]
    SetDisplaySpectrum.restype = None # void

except AttributeError as e:
    print(f"FATAL: Error defining function prototype in dp5_api.py: {e}")
    # Set all to None if any attribute error occurs to prevent partial loading
    ( ConnectToDefaultDPP, ConnectToDPP, ConnectToDPPIndex, CloseConnection, CountDppDevices,
      ClearData, EnableMCA, DisableMCA, RequestSpectrumData, AcquireSpectrum, ConsoleSpectrum,
      GetDppStatus, DppStatusToString, DppStatusToStruct, GetDppSerialNumber,
      ReadDppConfigurationFromHardware, DppHwConfigToString, PresetModeToString,
      SendCommandString, SendConfigFileToDpp, SendScaToDpp, ShortenCfgCmds, DisplayPresets,
      ReadConfigFile, GetStartTime, SaveMCADataToFile, SetDisplayCfg, SetDisplayDebugInfo,
      SetDisplaySpectrum ) = (None,) * 29
    sys.exit(1)

# --- Helper Functions ---

# Helper to convert ctypes Spec to numpy array (from original code)
def spec_to_numpy(spec_struct: Spec) -> np.ndarray:
    """Converts a ctypes Spec structure to a NumPy array."""
    if not spec_struct:
        return np.array([], dtype=np.int32)
    num_channels = spec_struct.CHANNELS
    if num_channels <= 0 or num_channels > MAX_BUFFER_DATA:
        # Return empty or handle error appropriately
        return np.array([], dtype=np.int32)
    # Copy the valid part of the data
    return np.ctypeslib.as_array(spec_struct.DATA)[:num_channels].copy()

# Helper for SendCommandString based on user request
def send_ascii_command(command_string: str) -> bool:
    """
    Sends a single ASCII command string to the connected DP5.

    Args:
        command_string (str): The ASCII command (e.g., "PRET=10.0;").

    Returns:
        bool: True on success, False otherwise.

    Raises:
        RuntimeError: If the API or SendCommandString function is not loaded.
    """
    if not _dp5_lib or not SendCommandString:
        raise RuntimeError("DP5 API or SendCommandString function not loaded.")

    if not command_string:
        print("Warning: Attempted to send empty command string.")
        return False

    try:
        # Encode the string to ASCII bytes, required by c_char_p
        cmd_bytes = command_string.encode('ascii')
        result = SendCommandString(cmd_bytes)
        if result != 1: # API returns BOOL_TYPE (ubyte), 1 usually means true
            print(f"Error: SendCommandString failed for command: {command_string}")
            return False
        return True
    except Exception as e:
        print(f"Exception sending ASCII command '{command_string}': {e}")
        return False