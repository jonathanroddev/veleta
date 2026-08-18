"""The extension's built-in demo.

It is what somebody sees who installed the extension from the platform and
owns no kit, so "it silently does nothing" is the failure that matters. The
recording ships inside the package, so these tests check the real file, not
a fixture.
"""

import os
import unittest

import context
import playback


class TestBundledRecording(unittest.TestCase):
    def test_the_recording_ships_inside_the_extension(self):
        """It has to be under blender/ or the package will not carry it."""
        self.assertTrue(os.path.isfile(playback.DEMO_FILE))
        self.assertTrue(
            os.path.abspath(playback.DEMO_FILE).startswith(
                os.path.join(context.ROOT, "blender") + os.sep),
            "the demo recording must live under blender/ to be packaged")

    def test_it_loads_into_usable_frames(self):
        frames = playback.load_recording()
        self.assertGreater(len(frames), 50, "too short to demonstrate much")
        t, device, angles = frames[0]
        self.assertEqual(t, 0.0)
        self.assertTrue(device)
        self.assertEqual(len(angles), 3)

    def test_it_is_long_enough_to_look_alive(self):
        player = playback.DemoPlayer(playback.load_recording())
        self.assertGreater(player.length, 1.0)

    def test_the_angles_actually_move(self):
        """A recording of a motionless sensor would demonstrate nothing."""
        frames = playback.load_recording()
        yaws = [a[2] for _t, _d, a in frames]
        self.assertGreater(max(yaws) - min(yaws), 5.0)


class TestPlayer(unittest.TestCase):
    FRAMES = [(0.0, "A", (0.0, 0.0, 0.0)),
              (1.0, "A", (10.0, 0.0, 0.0)),
              (2.0, "A", (20.0, 0.0, 0.0))]

    def test_frames_come_out_on_the_clock_they_are_given(self):
        player = playback.DemoPlayer(self.FRAMES, loop=False)
        player.start(100.0)
        self.assertEqual(len(player.due(100.0)), 1)
        self.assertEqual(len(player.due(100.5)), 0)
        self.assertEqual(len(player.due(101.0)), 1)
        self.assertEqual(len(player.due(102.0)), 1)

    def test_it_loops_by_default(self):
        player = playback.DemoPlayer(self.FRAMES, loop=True)
        player.start(100.0)
        player.due(200.0)
        self.assertFalse(player.finished)
        self.assertTrue(player.due(300.0), "a looping demo must never stop")

    def test_without_looping_it_finishes(self):
        player = playback.DemoPlayer(self.FRAMES, loop=False)
        player.start(100.0)
        player.due(200.0)
        self.assertTrue(player.finished)
        self.assertEqual(player.due(300.0), [])

    def test_nothing_comes_out_before_start(self):
        player = playback.DemoPlayer(self.FRAMES)
        self.assertEqual(player.due(100.0), [])

    def test_an_empty_recording_is_finished_not_broken(self):
        player = playback.DemoPlayer([], loop=True)
        player.start(100.0)
        self.assertTrue(player.finished)
        self.assertEqual(player.due(100.0), [])
        self.assertEqual(player.length, 0.0)


class TestMalformedInput(unittest.TestCase):
    def test_broken_lines_are_skipped_not_fatal(self):
        """A demo that refuses to start over one short line is worse than a
        demo missing a frame."""
        import tempfile
        good = ('{"t": 0.0, "line": "WT,0,0,0,0,0,0,1.0,2.0,3.0,0,0,0"}')
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            f.write("# a comment\n")
            f.write(good + "\n")
            f.write("not json\n")
            f.write('{"t": 1.0}\n')
            f.write('{"t": 1.0, "line": "too,short"}\n')
            f.write('{"t": 2.0, "line": "WT,0,0,0,0,0,0,x,y,z,0,0,0"}\n')
            f.write(good + "\n")
        self.addCleanup(os.unlink, path)
        self.assertEqual(len(playback.load_recording(path)), 2)


if __name__ == "__main__":
    unittest.main()
