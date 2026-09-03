"""config.env loader.

Same format the Blender bridges used — KEY=value, '#' comments, no quotes,
values taken verbatim to end of line — and still with no external
dependency. What is gone is the guesswork: those scripts ran inside
Blender's text editor, where `__file__` frequently does not exist, and had
to recover their own folder from the open text datablocks. The core is an
ordinary process, so the file is simply looked up in order:

    1. $VELETA_CORE_CONFIG, if it points at a file.
    2. config.env in the current working directory.
    3. config.env next to the package (core/config.env, the shipped one).
"""

import os

DEFAULTS = {
    # --- Sensor input (sensors -> core) ---
    "SOURCE": "udp",                 # udp | serial | file
    "LISTEN_HOST": "0.0.0.0",
    "LISTEN_PORT": "1399",
    "SERIAL_PORT": "",               # "" = find the one plugged-in port
    "BAUD_RATE": "115200",
    "SERIAL_DEVICE_ID": "wired",     # the cable carries no DeviceID; this is it
    "BLE_NAME": "",                  # peripheral to connect to; "" = first HM-10
    "BLE_ADDRESS": "",               # wins over BLE_NAME when set
    "BLE_CHAR": "0000ffe1-0000-1000-8000-00805f9b34fb",
    "BLE_DEVICE_ID": "",             # "" = use the peripheral's BLE name
    "BLE_TIMEOUT": "20",             # seconds to scan and connect

    # --- Output (core -> consumers) ---
    "CONTROL_HOST": "127.0.0.1",
    "CONTROL_PORT": "1400",
    "SUBSCRIPTION_TTL": "10",        # seconds a subscriber stays subscribed

    # --- Frame parsing (see docs/protocol.md) ---
    "FRAME_FORMAT": "auto",          # auto | fused | raw6
    "IDX_DEVICE": "0",
    "IDX_ACC_X": "1",
    "IDX_ACC_Y": "2",
    "IDX_ACC_Z": "3",
    "IDX_GYRO_X": "4",
    "IDX_GYRO_Y": "5",
    "IDX_GYRO_Z": "6",
    "IDX_ANGLE_X": "7",
    "IDX_ANGLE_Y": "8",
    "IDX_ANGLE_Z": "9",
    "MIN_FIELDS": "7",

    # --- Fusion, raw6 sensors only ---
    "ALPHA_ROLL_PITCH": "0.98",
    "GYRO_CALIB_SAMPLES": "50",

    # --- Reference pose calibration ---
    "AUTO_CALIBRATE": "1",
    "CALIB_COUNTDOWN": "3",
}


def find_config_path(explicit=None):
    """Return the path of the config.env to use, or None."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("VELETA_CORE_CONFIG")
    if env:
        candidates.append(env)
    candidates.append(os.path.join(os.getcwd(), "config.env"))
    candidates.append(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config.env"))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def load(explicit=None):
    """Read config.env over DEFAULTS. Returns (config_dict, path_or_None)."""
    cfg = dict(DEFAULTS)
    path = find_config_path(explicit)
    if path is None:
        return cfg, None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    return cfg, path
