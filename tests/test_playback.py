"""Recording and replaying the sensor stream.

The mode that makes the product demonstrable without hardware, testable in
CI, and debuggable from a file a user emailed in. The recording holds the
SENSOR stream, not the core's output, so replaying it exercises parsing,
fusion and calibration exactly as live hardware would.
"""

import json
import os
import tempfile
import unittest

import context
from vane_core.config import DEFAULTS
from vane_core.engine import Engine
from vane_core.recorder import Recorder
from vane_core.sources import FileSource


def fused_frame(device, roll, pitch, yaw):
    return (f"{device},0.01,0.02,0.98,1.0,2.0,3.0,"
            f"{roll},{pitch},{yaw},0.1,0.2,0.3")


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        self.addCleanup(os.unlink, self.path)

    def _record(self, lines, start=1000.0, step=0.02):
        rec = Recorder(self.path, note="test fixture")
        for i, line in enumerate(lines):
            rec.write(line, start + i * step)
        rec.close()
        return rec.count

    def test_what_is_recorded_is_what_is_replayed(self):
        lines = [fused_frame("WT53abc", i, 0, 0) for i in range(10)]
        self.assertEqual(self._record(lines), 10)
        source = FileSource(self.path, realtime=False)
        replayed = [line for line, _t in source.poll(max_batch=100)]
        self.assertEqual(replayed, lines)

    def test_timestamps_are_relative_to_the_first_frame(self):
        """So a recording is comparable between machines and can be
        replayed at its original rate."""
        self._record([fused_frame("A", 0, 0, 0)] * 3, start=1755000000.0)
        with open(self.path, encoding="utf-8") as f:
            entries = [json.loads(l) for l in f if not l.startswith("#")]
        self.assertEqual(entries[0]["t"], 0.0)
        self.assertAlmostEqual(entries[2]["t"], 0.04, places=6)

    def test_a_recording_drives_the_engine_with_no_hardware(self):
        self._record([fused_frame("WT53abc", 30, -12, 45)] * 5)
        engine = Engine(dict(DEFAULTS))
        source = FileSource(self.path, realtime=False)
        poses = [engine.feed(line, now=t)
                 for line, t in source.poll(max_batch=100)]
        poses = [p for p in poses if p is not None]
        self.assertEqual(len(poses), 5)
        self.assertEqual(poses[0].device, "WT53abc")
        self.assertAlmostEqual(poses[0].angles[0], 30.0, places=3)

    def test_a_finished_recording_reports_itself_exhausted(self):
        """That is what makes `--play` terminate instead of idling."""
        self._record([fused_frame("A", 0, 0, 0)] * 3)
        source = FileSource(self.path, realtime=False)
        source.poll(max_batch=100)
        self.assertTrue(source.exhausted)
        self.assertEqual(source.poll(), [])

    def test_looping_never_exhausts(self):
        self._record([fused_frame("A", 0, 0, 0)] * 3)
        source = FileSource(self.path, realtime=False, loop=True)
        for _ in range(3):
            self.assertTrue(source.poll(max_batch=100))
        self.assertFalse(source.exhausted)

    def test_comments_and_broken_lines_are_skipped(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("# a note\n")
            f.write(json.dumps({"t": 0.0, "line": fused_frame("A", 1, 2, 3)}) + "\n")
            f.write("this is not json\n")
            f.write(json.dumps({"t": 0.1}) + "\n")          # no line
            f.write("\n")
            f.write(json.dumps({"t": 0.2, "line": fused_frame("A", 4, 5, 6)}) + "\n")
        source = FileSource(self.path, realtime=False)
        self.assertEqual(len(source.poll(max_batch=100)), 2)


class TestShippedSamples(unittest.TestCase):
    """Whatever is in samples/ has to actually play, or the demo the buyer
    is pointed at is broken."""

    def test_every_sample_replays_into_poses(self):
        folder = os.path.join(context.ROOT, "samples")
        samples = [f for f in sorted(os.listdir(folder))
                   if f.endswith(".jsonl")]
        self.assertTrue(samples, "no sample recordings shipped")
        for name in samples:
            with self.subTest(sample=name):
                engine = Engine(dict(DEFAULTS))
                source = FileSource(os.path.join(folder, name),
                                    realtime=False)
                frames = source.poll(max_batch=100000)
                self.assertTrue(frames, f"{name} holds no frames")
                poses = [engine.feed(line, now=t) for line, t in frames]
                self.assertTrue([p for p in poses if p is not None],
                                f"{name} produced no pose")


if __name__ == "__main__":
    unittest.main()
