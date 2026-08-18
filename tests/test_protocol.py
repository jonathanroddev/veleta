"""The core <-> consumer protocol, over real sockets.

This is the seam the licence separation rests on: the extension is a
consumer that talks to an independent program over a documented protocol.
If that link only worked in theory the separation would be a story rather
than a fact, so it is tested with the real client, the real server and real
datagrams — the extension's client module imports no `bpy`, which is what
makes that possible outside Blender.
"""

import threading
import time
import unittest

import context
from client import CoreClient, version_warning
from vane_core import PROTOCOL_VERSION, __version__
from vane_core.config import DEFAULTS
from vane_core.engine import Engine
from vane_core.server import Server


def fused_frame(device, roll, pitch, yaw):
    return (f"{device},0.01,0.02,0.98,1.0,2.0,3.0,"
            f"{roll},{pitch},{yaw},0.1,0.2,0.3")


class CoreHarness:
    """A core running in a thread, on a port the OS picks."""

    def __init__(self):
        self.engine = Engine(dict(DEFAULTS))
        self.server = Server("127.0.0.1", 0, self.engine, ttl=5.0)
        self.port = self.server.port
        self._stop = threading.Event()
        self._pending = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            self.server.poll()
            with self._lock:
                lines, self._pending = self._pending, []
            for line in lines:
                pose = self.engine.feed(line)
                if pose is not None:
                    self.server.broadcast(pose)
            time.sleep(0.002)

    def emit(self, line):
        with self._lock:
            self._pending.append(line)

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)
        self.server.close()


class TestProtocol(unittest.TestCase):
    def setUp(self):
        self.core = CoreHarness()
        self.addCleanup(self.core.close)
        self.client = CoreClient("127.0.0.1", self.core.port, ttl=5.0)
        self.addCleanup(self.client.close)

    def _collect(self, seconds=1.0, want=1):
        poses = []
        deadline = time.time() + seconds
        while time.time() < deadline and len(poses) < want:
            poses.extend(self.client.poll())
            time.sleep(0.005)
        return poses

    def test_connect_returns_the_core_version(self):
        hello = self.client.connect()
        self.assertTrue(hello["ok"])
        self.assertEqual(hello["version"], __version__)
        self.assertEqual(hello["protocol"], PROTOCOL_VERSION)

    def test_a_subscriber_receives_poses(self):
        self.client.connect()
        for i in range(5):
            self.core.emit(fused_frame("WT53abc", 10, 0, 0))
            time.sleep(0.01)
        poses = self._collect(want=1)
        self.assertTrue(poses, "no pose reached the subscriber")
        self.assertEqual(poses[0]["dev"], "WT53abc")
        self.assertEqual(len(poses[0]["q"]), 4)

    def test_nothing_is_streamed_to_someone_who_never_asked(self):
        """The core streams to subscribers, not to the network."""
        self.core.emit(fused_frame("WT53abc", 10, 0, 0))
        time.sleep(0.05)
        self.assertEqual(self._collect(seconds=0.2), [])

    def test_calibrate_travels_from_the_consumer_to_the_core(self):
        """The user strikes the pose in Blender and presses a button; the
        zeroing happens in the core. That round trip is this test."""
        self.client.connect()
        self.core.emit(fused_frame("WT53abc", 30, 0, 0))
        self._collect(want=1)
        reply = self.client.command("calibrate")
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["calibrated"], 1)

    def test_devices_command_lists_what_the_core_has_seen(self):
        self.client.connect()
        self.core.emit(fused_frame("WT53abc", 0, 0, 0))
        self._collect(want=1)
        reply = self.client.command("devices")
        self.assertTrue(reply["ok"])
        self.assertEqual([d["id"] for d in reply["devices"]], ["WT53abc"])

    def test_recentering_an_unknown_sensor_answers_instead_of_hanging(self):
        self.client.connect()
        reply = self.client.command("recenter", device="ghost")
        self.assertFalse(reply["ok"])
        self.assertIn("unknown device", reply["error"])

    def test_an_unknown_command_is_answered_not_ignored(self):
        self.client.connect()
        reply = self.client.command("selfdestruct")
        self.assertFalse(reply["ok"])

    def test_malformed_datagrams_do_not_take_the_core_down(self):
        import socket
        raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for junk in (b"", b"not json", b"[1,2,3]", b"\x00\xff", b"{"):
            raw.sendto(junk, ("127.0.0.1", self.core.port))
        raw.close()
        time.sleep(0.05)
        hello = self.client.connect()      # still answering afterwards
        self.assertTrue(hello["ok"])

    def test_unsubscribing_stops_the_stream(self):
        self.client.connect()
        self.core.emit(fused_frame("WT53abc", 0, 0, 0))
        self.assertTrue(self._collect(want=1))
        self.client.close()
        time.sleep(0.05)
        self.client = CoreClient("127.0.0.1", self.core.port, ttl=5.0)
        self.core.emit(fused_frame("WT53abc", 0, 0, 0))
        time.sleep(0.05)
        self.assertEqual(self._collect(seconds=0.2), [])


class TestVersionCheck(unittest.TestCase):
    """Old firmware against new software is the fault this prevents."""

    def test_matching_versions_say_nothing(self):
        self.assertIsNone(version_warning("0.1.0", {"version": "0.1.0"}))

    def test_a_mismatch_names_both_sides(self):
        msg = version_warning("0.2.0", {"version": "0.1.0"})
        self.assertIsNotNone(msg)
        self.assertIn("0.1.0", msg)
        self.assertIn("0.2.0", msg)

    def test_no_hello_means_no_claim(self):
        self.assertIsNone(version_warning("0.1.0", None))


if __name__ == "__main__":
    unittest.main()
