"""Sensor frame parsing: the sensors -> core half of the protocol.

Straight port of the parsing the WiFi bridge did inside Blender, minus
`bpy`. The rule it enforces has not changed and is the reason this is a
module of its own: **a different CSV layout is a configuration change**
(the IDX_* keys), never a change to this parser. See docs/protocol.md.
"""


class Layout:
    """Field positions and profile thresholds, derived from config.env."""

    def __init__(self, cfg):
        self.format = str(cfg["FRAME_FORMAT"]).strip().lower()
        self.idx_device = int(cfg["IDX_DEVICE"])
        self.idx_acc = (int(cfg["IDX_ACC_X"]), int(cfg["IDX_ACC_Y"]),
                        int(cfg["IDX_ACC_Z"]))
        self.idx_gyro = (int(cfg["IDX_GYRO_X"]), int(cfg["IDX_GYRO_Y"]),
                         int(cfg["IDX_GYRO_Z"]))
        self.idx_angle = (int(cfg["IDX_ANGLE_X"]), int(cfg["IDX_ANGLE_Y"]),
                          int(cfg["IDX_ANGLE_Z"]))
        self.min_fields = int(cfg["MIN_FIELDS"])
        # Derived from the indices so there is no second place to keep in
        # sync when someone adjusts an IDX_*.
        self.need_fused = max(self.idx_angle) + 1
        self.need_raw6 = max(max(self.idx_acc), max(self.idx_gyro)) + 1

    def profile_for(self, n_fields):
        """Which profile a frame of `n_fields` follows, or None.

        'auto' prefers `fused` when the frame is long enough to carry
        angles: if the sensor already did the fusion, trust it rather than
        redoing it here.
        """
        if self.format == "fused":
            return "fused" if n_fields >= self.need_fused else None
        if self.format == "raw6":
            return "raw6" if n_fields >= self.need_raw6 else None
        if n_fields >= self.need_fused:
            return "fused"
        if n_fields >= self.need_raw6:
            return "raw6"
        return None


class Reading:
    """One parsed frame. `angles` is set for `fused`, `accel`/`gyro` for
    `raw6`; the other is None."""

    __slots__ = ("device", "profile", "accel", "gyro", "angles")

    def __init__(self, device, profile, accel=None, gyro=None, angles=None):
        self.device = device
        self.profile = profile
        self.accel = accel
        self.gyro = gyro
        self.angles = angles

    def __repr__(self):
        return (f"Reading({self.device!r}, {self.profile!r}, "
                f"accel={self.accel}, gyro={self.gyro}, angles={self.angles})")


def parse_line(line, layout, default_device=None):
    """Parse one CSV line into a Reading, or None if it is unusable.

    `default_device` names the device when the layout carries no DeviceID,
    which is the wired case: a cable carries exactly one sensor, so the
    transport already identifies it (docs/protocol.md).
    """
    if not line:
        return None
    parts = line.strip().split(",")
    if len(parts) < layout.min_fields:
        return None
    profile = layout.profile_for(len(parts))
    if profile is None:
        return None
    try:
        if default_device is None:
            device = parts[layout.idx_device].strip()
        else:
            device = default_device
        if not device:
            return None
        if profile == "fused":
            return Reading(device, profile,
                           angles=tuple(float(parts[i]) for i in layout.idx_angle))
        return Reading(device, profile,
                       accel=tuple(float(parts[i]) for i in layout.idx_acc),
                       gyro=tuple(float(parts[i]) for i in layout.idx_gyro))
    except (ValueError, IndexError):
        return None


def last_line_of(datagram):
    """Decode a datagram and return its last complete line.

    Some firmwares batch several readings into one datagram; the freshest
    pose is the one worth having, so the rest are dropped.
    """
    try:
        text = datagram.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
    if not text:
        return None
    return text.splitlines()[-1].strip()
