"""The complementary filter, checked against attitudes it did not see.

This is the test the project has had informally since the fake sensor was
written: build an accelerometer reading by projecting gravity onto a known
attitude, feed it through the filter, and require the filter to return the
attitude that generated it. That makes the emitter a fixture rather than
just a traffic generator.
"""

import math
import unittest

import context
from vane_core.fusion import DeviceFusion


def gravity_for(roll_deg, pitch_deg):
    """Accelerometer reading, in g, for a sensor held at this attitude."""
    r, p = math.radians(roll_deg), math.radians(pitch_deg)
    return (-math.sin(p), math.sin(r) * math.cos(p),
            math.cos(r) * math.cos(p))


class TestFusion(unittest.TestCase):
    def _settled(self, roll, pitch, samples=50):
        f = DeviceFusion(alpha=0.98, bias_samples=samples)
        accel = gravity_for(roll, pitch)
        out = None
        for _ in range(samples + 200):
            out = f.update(accel, (0.0, 0.0, 0.0), 0.02)
        return f, out

    def test_recovers_the_attitude_that_made_the_reading(self):
        for roll, pitch in [(0, 0), (30, 0), (0, -25), (15, 40), (-60, 10)]:
            with self.subTest(roll=roll, pitch=pitch):
                _, out = self._settled(roll, pitch)
                self.assertAlmostEqual(out[0], roll, delta=0.3)
                self.assertAlmostEqual(out[1], pitch, delta=0.3)

    def test_nothing_comes_out_until_the_bias_is_known(self):
        f = DeviceFusion(alpha=0.98, bias_samples=10)
        accel = gravity_for(0, 0)
        for i in range(10):
            self.assertIsNone(f.update(accel, (1.0, 1.0, 1.0), 0.02),
                              f"emitted a pose at sample {i}, before the "
                              f"bias was estimated")
        self.assertTrue(f.ready)

    def test_a_constant_gyro_offset_is_removed_as_bias(self):
        """The whole point of the still period: an unremoved offset would
        integrate straight into yaw drift."""
        f = DeviceFusion(alpha=0.98, bias_samples=20)
        accel = gravity_for(0, 0)
        offset = (0.0, 0.0, 4.0)     # 4 deg/s of pure bias on the yaw gyro
        for _ in range(20):
            f.update(accel, offset, 0.02)
        for _ in range(500):         # 10 s that would be 40 deg of drift
            out = f.update(accel, offset, 0.02)
        self.assertAlmostEqual(out[2], 0.0, delta=0.05)

    def test_yaw_integrates_when_the_sensor_actually_turns(self):
        f = DeviceFusion(alpha=0.98, bias_samples=10)
        accel = gravity_for(0, 0)
        for _ in range(10):
            f.update(accel, (0.0, 0.0, 0.0), 0.02)
        for _ in range(500):         # 10 s at 9 deg/s = 90 deg
            out = f.update(accel, (0.0, 0.0, 9.0), 0.02)
        self.assertAlmostEqual(out[2], 90.0, delta=0.2)

    def test_seeds_from_the_accelerometer_not_from_flat(self):
        """Without seeding, the filter spends its first second crawling
        from 'flat' to the real attitude."""
        f = DeviceFusion(alpha=0.98, bias_samples=1)
        accel = gravity_for(45, 0)
        f.update(accel, (0, 0, 0), 0.02)      # consumed by the bias estimate
        first = f.update(accel, (0, 0, 0), 0.02)
        self.assertAlmostEqual(first[0], 45.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
