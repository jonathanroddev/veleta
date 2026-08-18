"""Serial sensor source — the wired bench.

This is the only place in the product that imports `pyserial`, and it is
reached only through `open_serial_source()`. Before the core existed this
import lived inside Blender, which meant installing a package into
Blender's own bundled Python — a genuinely awkward step that the split
removes.
"""

import time

import serial  # noqa: F401  (imported lazily by sources/__init__.py)


class SerialSource:
    name = "serial"

    def __init__(self, port, baud=115200, settle=2.0):
        self.port_name = port
        self.baud = int(baud)
        self.ser = serial.Serial(port, int(baud), timeout=0)
        if settle:
            # Opening the port resets the board; give it time to boot before
            # trusting what comes out of it.
            time.sleep(settle)
        self.ser.reset_input_buffer()
        self._buf = b""

    def describe(self):
        return f"serial {self.port_name} @ {self.baud}"

    def poll(self, max_batch=200):
        out = []
        try:
            chunk = self.ser.read(4096)
        except Exception:
            return out
        if chunk:
            self._buf += chunk
        while len(out) < max_batch and b"\n" in self._buf:
            raw, _, self._buf = self._buf.partition(b"\n")
            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                out.append((line, time.time()))
        return out

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass
