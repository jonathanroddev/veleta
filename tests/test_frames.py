"""Frame parsing, and the rule that a layout difference is configuration.

Every one of these would previously have tempted somebody to patch the
parser. The point of the IDX_* keys is that none of them needs to.
"""

import unittest

import context
from veleta_core.config import DEFAULTS
from veleta_core.frames import Layout, last_line_of, parse_line

FUSED = "WT53abc,0.01,0.02,0.98,1.0,2.0,3.0,10.5,-20.25,30.0,0.1,0.2,0.3"
RAW6 = "ESP32_A,0.01,0.02,0.98,1.0,2.0,3.0"


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.layout = Layout(dict(DEFAULTS))

    def test_fused_frame(self):
        r = parse_line(FUSED, self.layout)
        self.assertEqual(r.device, "WT53abc")
        self.assertEqual(r.profile, "fused")
        self.assertEqual(r.angles, (10.5, -20.25, 30.0))

    def test_raw6_frame(self):
        r = parse_line(RAW6, self.layout)
        self.assertEqual(r.device, "ESP32_A")
        self.assertEqual(r.profile, "raw6")
        self.assertEqual(r.accel, (0.01, 0.02, 0.98))
        self.assertEqual(r.gyro, (1.0, 2.0, 3.0))

    def test_raw6_is_a_prefix_of_fused(self):
        """The two profiles share the same indices; that is the whole
        reason raw6 was defined as a prefix of the WitMotion layout."""
        self.assertEqual(parse_line(RAW6, self.layout).accel,
                         parse_line(FUSED, self.layout.__class__(
                             dict(DEFAULTS, FRAME_FORMAT="raw6"))).accel)

    def test_junk_is_rejected_not_crashed(self):
        for bad in ("", "   ", "hello", "a,b,c", "WT,1,2,3,4,5,x",
                    "WT53abc,0.1,0.2,0.3,0.4,0.5"):
            with self.subTest(line=bad):
                self.assertIsNone(parse_line(bad, self.layout))

    def test_forced_profile(self):
        raw_only = Layout(dict(DEFAULTS, FRAME_FORMAT="raw6"))
        r = parse_line(FUSED, raw_only)
        self.assertEqual(r.profile, "raw6",
                         "FRAME_FORMAT=raw6 must ignore the sensor's angles")

    def test_a_reshuffled_layout_is_config_not_code(self):
        """A firmware that puts the DeviceID last and the angles first."""
        moved = Layout(dict(DEFAULTS, IDX_DEVICE="9", IDX_ANGLE_X="0",
                            IDX_ANGLE_Y="1", IDX_ANGLE_Z="2",
                            IDX_ACC_X="3", IDX_ACC_Y="4", IDX_ACC_Z="5",
                            IDX_GYRO_X="6", IDX_GYRO_Y="7", IDX_GYRO_Z="8",
                            MIN_FIELDS="10"))
        r = parse_line("10.5,-20.25,30.0,0.01,0.02,0.98,1,2,3,WT53abc", moved)
        self.assertEqual(r.device, "WT53abc")
        self.assertEqual(r.angles, (10.5, -20.25, 30.0))

    def test_wired_frames_have_no_device_id(self):
        """A cable carries exactly one sensor, so the transport is the id."""
        layout = Layout(dict(DEFAULTS, MIN_FIELDS="6", IDX_ACC_X="0",
                             IDX_ACC_Y="1", IDX_ACC_Z="2", IDX_GYRO_X="3",
                             IDX_GYRO_Y="4", IDX_GYRO_Z="5",
                             FRAME_FORMAT="raw6"))
        r = parse_line("0.01,0.02,0.98,1.0,2.0,3.0", layout,
                       default_device="wired")
        self.assertEqual(r.device, "wired")
        self.assertEqual(r.accel, (0.01, 0.02, 0.98))


class TestDatagrams(unittest.TestCase):
    def test_batched_datagram_keeps_the_freshest_line(self):
        data = (RAW6 + "\r\n" + FUSED + "\r\n").encode()
        self.assertEqual(last_line_of(data), FUSED)

    def test_empty_and_binary_are_survivable(self):
        """Binary noise on the port does not have to be rejected by
        last_line_of — it decodes to junk, and the parser is what refuses
        it. What matters is that nothing downstream ever sees a Reading."""
        self.assertIsNone(last_line_of(b""))
        layout = Layout(dict(DEFAULTS))
        for noise in (b"\x00\xff\xfe", b"\x80\x81", b"\n\n\n"):
            with self.subTest(noise=noise):
                line = last_line_of(noise)
                self.assertIsNone(parse_line(line, layout))


if __name__ == "__main__":
    unittest.main()
