"""Recording the sensor stream to a .jsonl sample.

One JSON object per line: {"t": <seconds>, "line": "<the CSV frame>"}.
The timestamps are relative to the first frame, so a recording is
comparable between machines and can be replayed at its original rate.
"""

import json


class Recorder:
    def __init__(self, path, note=None):
        self.path = path
        self._f = open(path, "w", encoding="utf-8")
        self._t0 = None
        self.count = 0
        if note:
            self._f.write("# " + str(note).replace("\n", " ") + "\n")

    def write(self, line, t):
        if self._t0 is None:
            self._t0 = t
        json.dump({"t": round(t - self._t0, 6), "line": line}, self._f)
        self._f.write("\n")
        self.count += 1

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass
