"""Shared guts of the diagnostic readers.

`read_udp.py` and `read_serial.py` exist to answer one question before you
trust anything downstream: **does what this sensor actually sends match the
indices in `config.env`?** They used to dump raw lines and leave you
counting commas. They now dump the raw line *and* what the core's own
parser makes of it, using the real `Layout`, so the answer is on screen.

They still print the raw text first, always. That is the point of a
diagnostic reader: if the parser and the sensor disagree, you need to see
what arrived, not what the parser wished had arrived.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veleta_core.config import load as load_config      # noqa: E402
from veleta_core.frames import Layout, parse_line       # noqa: E402


def load_layout():
    """The same Layout the core would use. Returns (layout, path_or_None)."""
    cfg, path = load_config()
    return Layout(cfg), path


def interpret(line, layout, default_device=None):
    """One short line saying how the configured layout reads this frame."""
    reading = parse_line(line, layout, default_device)
    if reading is None:
        return "UNPARSED — no profile matches, or a field is not a number"
    if reading.profile == "fused":
        ang = ", ".join(f"{v:8.2f}" for v in reading.angles)
        return f"fused  dev={reading.device:<12} ang=({ang})"
    acc = ", ".join(f"{v:7.3f}" for v in reading.accel)
    gyr = ", ".join(f"{v:8.2f}" for v in reading.gyro)
    return (f"raw6   dev={reading.device:<12} acc=({acc})  gyro=({gyr})")


class Summary:
    """What was seen, so you do not have to read 400 lines to find out."""

    def __init__(self, layout, default_device=None):
        self.layout = layout
        self.default_device = default_device
        self.lines = 0
        self.unparsed = 0
        self.field_counts = {}
        self.devices = {}
        self.batched = 0

    def note(self, line):
        """Record one line and return its interpretation."""
        self.lines += 1
        n = len(line.split(","))
        self.field_counts[n] = self.field_counts.get(n, 0) + 1
        reading = parse_line(line, self.layout, self.default_device)
        if reading is None:
            self.unparsed += 1
        else:
            self.devices.setdefault(reading.device, reading.profile)
        return interpret(line, self.layout, self.default_device)

    def note_batch(self, n_lines):
        if n_lines > 1:
            self.batched += 1

    def report(self, prefix):
        print(f"\n{prefix} {self.lines} lines.", flush=True)
        if not self.lines:
            print(f"{prefix} Nothing arrived. Check power, address and port.",
                  flush=True)
            return
        counts = ", ".join(f"{n} fields x{c}"
                           for n, c in sorted(self.field_counts.items()))
        print(f"{prefix} Field counts: {counts}", flush=True)
        if self.devices:
            for dev, profile in sorted(self.devices.items()):
                print(f"{prefix} Device '{dev}' -> profile {profile}",
                      flush=True)
        if self.batched:
            print(f"{prefix} {self.batched} datagram(s) carried more than one "
                  f"line; the core keeps the last (freshest) one.", flush=True)
        if self.unparsed:
            print(f"{prefix} {self.unparsed} line(s) UNPARSED. If the sensor "
                  f"is fine, your IDX_* do not match its layout — fix "
                  f"config.env, never the parser.", flush=True)
        else:
            print(f"{prefix} Every line parsed with the configured indices.",
                  flush=True)
