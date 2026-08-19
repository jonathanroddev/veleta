"""File playback — the core fed from a recording instead of from hardware.

Three jobs at once, which is why it was worth building early: a fixture
the tests can run against, a way to reproduce a fault from a recording a
user sent without having their hardware on the desk, and a working setup
when the sensor is flat, broken or in another room.

Not, note, the answer for somebody who has the extension and no kit: the
core ships with the hardware, so that person has no core to run this with.
The extension carries its own recording for them (`blender/playback.py`).

The recording holds the **sensor** stream, not the core's output, so
playing it back exercises parsing, fusion and calibration exactly as live
hardware would. Format in docs/protocol.md.
"""

import json
import time


class FileSource:
    name = "file"

    def __init__(self, path, loop=False, speed=1.0, realtime=True):
        self.path = path
        self.loop = bool(loop)
        self.speed = float(speed) or 1.0
        self.realtime = bool(realtime)
        self.entries = self._read(path)
        self.exhausted = not self.entries
        self._i = 0
        self._started = None

    @staticmethod
    def _read(path):
        entries = []
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
                entries.append((float(obj.get("t", 0.0)), line))
        return entries

    def describe(self):
        return f"file {self.path} ({len(self.entries)} frames)"

    def poll(self, max_batch=200):
        """Return the frames whose time has come.

        With realtime=False every remaining frame is returned at once, which
        is what the tests want: a recording replays deterministically and in
        milliseconds instead of in its original duration.
        """
        if self.exhausted:
            return []
        out = []
        now = time.time()
        if self._started is None:
            self._started = now
        while self._i < len(self.entries) and len(out) < max_batch:
            t_rec, line = self.entries[self._i]
            if self.realtime:
                due = self._started + (t_rec - self.entries[0][0]) / self.speed
                if now < due:
                    break
                stamp = due
            else:
                stamp = self.entries[0][0] + (t_rec - self.entries[0][0])
            out.append((line, stamp))
            self._i += 1
        if self._i >= len(self.entries):
            if self.loop:
                self._i = 0
                self._started = time.time()
            else:
                self.exhausted = True
        return out

    def close(self):
        pass
