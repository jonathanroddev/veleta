"""BLE frame reassembly, and why the first fragment must be thrown away.

The HM-10 hands the core 20-byte ATT notifications, so a 45-byte frame
almost never arrives whole. None of this needs a radio: the reassembly is
a pure function of the byte stream, and that is the half that breaks.
"""

import unittest

import context
from veleta_core.config import DEFAULTS
from veleta_core.frames import Layout, parse_line
from veleta_core.sources.ble import HM10_CHAR, HM10_SERVICE, LineAssembler

FRAME = "-0.3015,-0.4404,0.8176,0.1145,0.5725,0.6947"


def wired_layout():
    """The 6-field, no-DeviceID layout BLE shares with the wired bench."""
    cfg = dict(DEFAULTS)
    cfg.update({"FRAME_FORMAT": "raw6", "MIN_FIELDS": "6",
                "IDX_ACC_X": "0", "IDX_ACC_Y": "1", "IDX_ACC_Z": "2",
                "IDX_GYRO_X": "3", "IDX_GYRO_Y": "4", "IDX_GYRO_Z": "5"})
    return Layout(cfg)


def chunks(data, size=20):
    """Exactly how the module delivers: fixed-size ATT notifications."""
    return [data[i:i + size] for i in range(0, len(data), size)]


class TestReassembly(unittest.TestCase):
    def setUp(self):
        self.a = LineAssembler()

    def test_first_partial_line_is_discarded(self):
        """Connecting mid-frame must not yield that frame."""
        out = self.a.feed(b"406,0.7099\r\n" + FRAME.encode() + b"\r\n")
        self.assertEqual(out, [FRAME])

    def test_frame_split_across_notifications(self):
        self.a.feed(b"junk\n")                     # get past the sync
        got = []
        for c in chunks((FRAME + "\r\n").encode()):
            got += self.a.feed(c)
        self.assertEqual(got, [FRAME])

    def test_several_frames_in_one_notification(self):
        self.a.feed(b"junk\n")
        out = self.a.feed(f"{FRAME}\r\n{FRAME}\r\n".encode())
        self.assertEqual(out, [FRAME, FRAME])

    def test_partial_tail_is_held_not_emitted(self):
        self.a.feed(b"junk\n")
        self.assertEqual(self.a.feed(b"-0.3015,-0.44"), [])
        self.assertEqual(self.a.feed(b"04,0.8176,0.1145,0.5725,0.6947\r\n"),
                         [FRAME])

    def test_blank_lines_are_skipped(self):
        self.a.feed(b"junk\n")
        self.assertEqual(self.a.feed(b"\r\n\r\n" + FRAME.encode() + b"\r\n"),
                         [FRAME])

    def test_a_realistic_stream_loses_nothing(self):
        self.a.feed(b"junk\n")
        stream = ("".join(FRAME + "\r\n" for _ in range(50))).encode()
        got = []
        for c in chunks(stream):
            got += self.a.feed(c)
        self.assertEqual(got, [FRAME] * 50)


class TestWhySyncMatters(unittest.TestCase):
    """The regression this guard exists for, stated as a test.

    Measured on 2026-08-24: over-running the link makes the HM-10 drop
    BYTES mid-line, not whole frames. The debris still parses.
    """

    def test_a_truncated_frame_still_parses_as_six_fields(self):
        debris = "44,-0.4360,0.8091,-0.0229,1.0382,0.9084"   # from the wire
        reading = parse_line(debris, wired_layout(), default_device="ble")
        self.assertIsNotNone(reading, "debris parses — that is the danger")
        self.assertEqual(reading.accel[0], 44.0)   # 44 g, from a cut "-0.3044"

    def test_the_assembler_never_emits_that_debris_at_connect(self):
        a = LineAssembler()
        out = a.feed(b"44,-0.4360,0.8091,-0.0229,1.0382,0.9084\r\n"
                     + FRAME.encode() + b"\r\n")
        self.assertEqual(out, [FRAME])


class TestModuleContract(unittest.TestCase):
    def test_uuids_are_the_hm10_ones(self):
        self.assertTrue(HM10_SERVICE.startswith("0000ffe0"))
        self.assertTrue(HM10_CHAR.startswith("0000ffe1"))

    def test_importing_the_source_does_not_need_bleak(self):
        """`bleak` must stay behind the lazy import, like pyserial."""
        import sys
        self.assertNotIn("bleak", sys.modules)


if __name__ == "__main__":
    unittest.main()
