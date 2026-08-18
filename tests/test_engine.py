"""The engine: routing, fusion and calibration, with no sockets involved."""

import unittest

import context
from vane_core import quat
from vane_core.config import DEFAULTS
from vane_core.engine import Engine


def fused_frame(device, roll, pitch, yaw):
    return (f"{device},0.01,0.02,0.98,1.0,2.0,3.0,"
            f"{roll},{pitch},{yaw},0.1,0.2,0.3")


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(dict(DEFAULTS))

    def test_one_socket_serves_several_sensors(self):
        """Two devices, two profiles, one stream: each keeps its own state.
        This is what makes the suit a matter of adding sensors, not code."""
        self.engine.feed(fused_frame("WT53abc", 10, 0, 0), now=1.0)
        for i in range(60):
            self.engine.feed("ESP32_A,0.0,0.0,1.0,0.0,0.0,0.0",
                             now=1.0 + i * 0.02)
        devices = {d["id"]: d for d in self.engine.device_list()}
        self.assertEqual(set(devices), {"WT53abc", "ESP32_A"})
        self.assertEqual(devices["WT53abc"]["profile"], "fused")
        self.assertEqual(devices["ESP32_A"]["profile"], "raw6")

    def test_calibration_makes_the_current_pose_zero(self):
        self.engine.feed(fused_frame("WT53abc", 30, -12, 45), now=1.0)
        self.assertEqual(self.engine.calibrate(), 1)
        pose = self.engine.feed(fused_frame("WT53abc", 30, -12, 45), now=1.1)
        rpy = quat.to_euler_zyx_degrees(pose.quaternion)
        for value in rpy:
            self.assertAlmostEqual(value, 0.0, places=6)

    def test_calibration_leaves_the_reported_angles_raw(self):
        """`rpy` is diagnostic: it says what the sensor reads, not what the
        object does. Zeroing it too would hide drift from the user."""
        self.engine.feed(fused_frame("WT53abc", 30, 0, 0), now=1.0)
        self.engine.calibrate()
        pose = self.engine.feed(fused_frame("WT53abc", 30, 0, 0), now=1.1)
        self.assertAlmostEqual(pose.angles[0], 30.0, places=6)

    def test_calibration_offsets_are_per_device(self):
        self.engine.feed(fused_frame("A", 30, 0, 0), now=1.0)
        self.engine.feed(fused_frame("B", 60, 0, 0), now=1.0)
        self.engine.recenter("A")
        pose_a = self.engine.feed(fused_frame("A", 30, 0, 0), now=1.1)
        pose_b = self.engine.feed(fused_frame("B", 60, 0, 0), now=1.1)
        self.assertAlmostEqual(quat.to_euler_zyx_degrees(pose_a.quaternion)[0],
                               0.0, places=6)
        self.assertAlmostEqual(quat.to_euler_zyx_degrees(pose_b.quaternion)[0],
                               60.0, places=4)

    def test_recentering_an_unknown_sensor_is_refused_not_crashed(self):
        self.assertFalse(self.engine.recenter("nobody"))

    def test_a_raw6_sensor_emits_nothing_until_its_bias_is_known(self):
        cfg = dict(DEFAULTS, GYRO_CALIB_SAMPLES="10")
        engine = Engine(cfg)
        for i in range(10):
            self.assertIsNone(
                engine.feed("ESP32_A,0.0,0.0,1.0,0.0,0.0,0.0", now=i * 0.02))
        self.assertIsNotNone(
            engine.feed("ESP32_A,0.0,0.0,1.0,0.0,0.0,0.0", now=0.22))

    def test_junk_never_reaches_a_consumer(self):
        for bad in ("", "garbage", "1,2,3", "A,B,C,D,E,F,G"):
            self.assertIsNone(self.engine.feed(bad, now=1.0))
        self.assertEqual(self.engine.device_list(), [])


if __name__ == "__main__":
    unittest.main()
