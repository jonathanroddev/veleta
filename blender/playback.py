"""The built-in demo: the extension moving something with no core at all.

WHY THIS EXISTS
    The core is proprietary and ships with the hardware kit. Without this,
    somebody who installs the extension on its own — from the extensions
    platform, having bought nothing — would find a panel that does
    literally nothing until they own a kit. That is a bad first impression
    and a poor answer to "what does this extension actually do?".

    So a short recording ships inside the package and the extension can
    replay it by itself. No sensors, no core, no network: it reads a file
    that sits next to this one and drives the object exactly as a live
    sensor would.

WHAT IT IS NOT
    Not a substitute for the core, and not a general-purpose reader. It
    replays angles that were already fused, from a file we ship and whose
    layout we control. There is no fusion here, no calibration, no device
    routing — that is the core's work, and duplicating it here is exactly
    what the split exists to avoid.

Imports no `bpy`, so it is tested outside Blender.
"""

import json
import os

# Field positions of the `fused` profile, from docs/protocol.md. Hardcoded
# on purpose: unlike the core, this reads ONE file, shipped inside this
# package, whose layout cannot change behind our backs. The project's rule
# that a layout is configuration applies to sensors in the wild, not to a
# fixture we author ourselves.
IDX_DEVICE = 0
IDX_ANGLES = (7, 8, 9)
MIN_FIELDS = 10

DEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "demo", "desk_wobble.jsonl")


def load_recording(path=None):
    """Read a bundled recording into [(t, device, (roll, pitch, yaw))].

    Malformed lines are skipped rather than fatal: a demo that refuses to
    start because one line is short is worse than a demo missing a frame.
    """
    path = path or DEMO_FILE
    frames = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            line = obj.get("line")
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < MIN_FIELDS:
                continue
            try:
                angles = tuple(float(parts[i]) for i in IDX_ANGLES)
                device = parts[IDX_DEVICE].strip()
                t = float(obj.get("t", 0.0))
            except (ValueError, IndexError):
                continue
            frames.append((t, device, angles))
    return frames


class DemoPlayer:
    """Replays a recording against a clock the caller provides.

    The clock is passed in rather than read here, for the same reason the
    core's filter takes its `dt`: it makes the thing testable in
    milliseconds instead of in the recording's real duration.
    """

    def __init__(self, frames, loop=True):
        self.frames = frames
        self.loop = loop
        self.finished = not frames
        self._i = 0
        self._started = None
        self._t0 = frames[0][0] if frames else 0.0

    @property
    def length(self):
        """Duration of the recording in seconds."""
        if not self.frames:
            return 0.0
        return self.frames[-1][0] - self._t0

    def start(self, now):
        self._started = now
        self._i = 0
        self.finished = not self.frames

    def due(self, now):
        """Frames whose time has come, as [(device, (roll, pitch, yaw))]."""
        if self.finished or self._started is None:
            return []
        out = []
        while self._i < len(self.frames):
            t, device, angles = self.frames[self._i]
            if now < self._started + (t - self._t0):
                break
            out.append((device, angles))
            self._i += 1
        if self._i >= len(self.frames):
            if self.loop:
                self._i = 0
                self._started = now
            else:
                self.finished = True
        return out
