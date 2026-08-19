"""The core's state: devices, fusion, calibration.

This is the piece that used to live inside the Blender scripts and is the
whole point of the core being a separate program. It knows nothing about
Blender, Godot, sockets or files: it is fed CSV lines and hands back
oriented poses.

WHAT IT DOES NOT DO — and deliberately so: the axis mapping (SIGN_* and
AXIS_MAP). How a sensor is mounted maps onto the *consumer's* axis
convention, and Blender (Z up) and Godot (Y up) do not share one. So the
core emits orientation in the sensor's own frame and each consumer maps it.
See docs/protocol.md.
"""

import time

from . import quat
from .frames import Layout, parse_line
from .fusion import DeviceFusion


class Pose:
    """One oriented reading, ready to be sent to consumers."""

    __slots__ = ("device", "profile", "quaternion", "angles", "t")

    def __init__(self, device, profile, quaternion, angles, t):
        self.device = device
        self.profile = profile
        self.quaternion = quaternion   # calibrated, sensor frame, (w,x,y,z)
        self.angles = angles           # uncalibrated (roll,pitch,yaw) degrees
        self.t = t

    def as_dict(self):
        return {
            "t": round(self.t, 6),
            "dev": self.device,
            "profile": self.profile,
            "q": [round(v, 6) for v in self.quaternion],
            "rpy": [round(v, 3) for v in self.angles],
        }


class Device:
    def __init__(self, device_id, profile):
        self.id = device_id
        self.profile = profile
        self.fusion = None       # DeviceFusion, raw6 only
        self.last_quat = None    # last measured orientation, uncalibrated
        self.offset = None       # inverse of the reference pose, or None
        self.last_t = None       # timestamp of the previous frame, for dt
        self.frames = 0


class Engine:
    def __init__(self, cfg, log=None):
        self.cfg = cfg
        self.layout = Layout(cfg)
        self.alpha = float(cfg["ALPHA_ROLL_PITCH"])
        self.bias_samples = int(cfg["GYRO_CALIB_SAMPLES"])
        self.devices = {}
        self._log = log or (lambda msg: None)

    # ---------- ingestion ----------
    def feed(self, line, now=None, default_device=None):
        """Parse and fuse one CSV line. Returns a Pose, or None when the
        line is unusable or the device is still estimating its gyro bias."""
        reading = parse_line(line, self.layout, default_device)
        if reading is None:
            return None
        if now is None:
            now = time.time()

        dev = self.devices.get(reading.device)
        if dev is None:
            dev = self.devices[reading.device] = Device(reading.device,
                                                        reading.profile)
            self._log(f"new sensor: {dev.id} [{dev.profile}]")
        dev.frames += 1

        dt = 0.02 if dev.last_t is None else max(1e-6, now - dev.last_t)
        dev.last_t = now

        if reading.profile == "raw6":
            if dev.fusion is None:
                dev.fusion = DeviceFusion(self.alpha, self.bias_samples)
                self._log(f"'{dev.id}': estimating gyro bias, KEEP IT STILL "
                          f"({self.bias_samples} samples)...")
            angles = dev.fusion.update(reading.accel, reading.gyro, dt)
            if angles is None:
                return None  # still estimating the bias; nothing to emit yet
        else:
            angles = reading.angles

        q = quat.from_euler_zyx_degrees(*angles)
        dev.last_quat = q
        corrected = quat.mul(dev.offset, q) if dev.offset is not None else q
        return Pose(dev.id, dev.profile, corrected, angles, now)

    # ---------- control ----------
    def calibrate(self):
        """Capture the current orientation of every known sensor as its
        reference pose (zero). Strike the pose first, then call this."""
        n = 0
        for dev in self.devices.values():
            if dev.last_quat is not None:
                dev.offset = quat.inverse(dev.last_quat)
                n += 1
        self._log(f"reference pose captured for {n} sensor(s)")
        return n

    def recenter(self, device_id):
        """Re-zero one sensor. This is also how the yaw drift of a raw6
        sensor is cancelled."""
        dev = self.devices.get(device_id)
        if dev is None or dev.last_quat is None:
            return False
        dev.offset = quat.inverse(dev.last_quat)
        self._log(f"sensor '{device_id}' recentered")
        return True

    def device_list(self):
        return [
            {
                "id": d.id,
                "profile": d.profile,
                "calibrated": d.offset is not None,
                "frames": d.frames,
                "ready": (d.fusion.ready if d.fusion is not None else True),
            }
            for d in sorted(self.devices.values(), key=lambda d: d.id)
        ]
