"""Choosing the serial port when nobody has said which one.

This is the step the first run actually stops at: the COM number is
assigned by Windows, is not guessable, and used to be typed into a
configuration file with Notepad. None of it needs a cable — the decision is
a pure function of the enumerated ports and the configured value.

Skipped when `pyserial` is absent: the module under test imports it, and it
is one of the core's two justified non-stdlib dependencies rather than
something the suite may assume.
"""

import unittest
from unittest import mock

import context                                        # noqa: F401

try:
    from veleta_core.sources import serial_source
except ImportError:                                   # pragma: no cover
    serial_source = None


class FakePort:
    """What `serial.tools.list_ports.comports()` hands back, as used here."""

    def __init__(self, device, description="", vid=None):
        self.device = device
        self.description = description
        self.vid = vid


@unittest.skipIf(serial_source is None, "pyserial is not installed")
class TestResolvePort(unittest.TestCase):
    def resolve(self, requested, candidates):
        return serial_source.resolve_port(requested, candidates)

    def test_explicit_port_is_used_as_written(self):
        port, auto = self.resolve("COM5", [FakePort("COM3", vid=1)])
        self.assertEqual(port, "COM5")
        self.assertFalse(auto)

    def test_explicit_port_absent_from_the_list_is_still_honoured(self):
        """Enumeration is not exhaustive everywhere, so it does not veto."""
        port, auto = self.resolve("/dev/ttyS9", [])
        self.assertEqual(port, "/dev/ttyS9")
        self.assertFalse(auto)

    def test_empty_and_one_candidate_auto_detects(self):
        port, auto = self.resolve("", [FakePort("COM7", vid=0x1a86)])
        self.assertEqual(port, "COM7")
        self.assertTrue(auto)

    def test_untouched_placeholder_counts_as_unset(self):
        """A config nobody edited names a device that does not exist."""
        port, auto = self.resolve("/dev/cu.usbserial-CHANGE_ME",
                                  [FakePort("COM7", vid=0x1a86)])
        self.assertEqual(port, "COM7")
        self.assertTrue(auto)

    def test_several_candidates_is_a_question_not_a_guess(self):
        with self.assertRaises(serial_source.SerialPortError) as caught:
            self.resolve("", [FakePort("COM3", "USB-SERIAL CH340", vid=1),
                              FakePort("COM4", "FT232R USB UART", vid=2)])
        message = str(caught.exception)
        self.assertIn("COM3", message)
        self.assertIn("COM4", message)
        self.assertIn("USB-SERIAL CH340", message)

    def test_no_candidates_says_so_rather_than_failing_to_open_nothing(self):
        with self.assertRaises(serial_source.SerialPortError) as caught:
            self.resolve("", [])
        self.assertIn("none could be found", str(caught.exception))


@unittest.skipIf(serial_source is None, "pyserial is not installed")
class TestCandidateFilter(unittest.TestCase):
    """What gets offered. A USB vendor id means somebody plugged it in."""

    def candidates(self, ports):
        with mock.patch("serial.tools.list_ports.comports",
                        return_value=ports):
            return [p.device for p in serial_source.list_candidates()]

    def test_built_in_ports_are_filtered_out(self):
        """COM1 on a desktop and macOS's Bluetooth-Incoming-Port are not
        sensors, and offering them makes the one real device ambiguous."""
        self.assertEqual(
            self.candidates([FakePort("COM1"),
                             FakePort("COM3", "USB-SERIAL CH340", vid=0x1a86)]),
            ["COM3"])

    def test_the_filter_never_empties_the_list(self):
        """A paired classic Bluetooth module carries no vendor id of its
        own and is a supported sensor, so an all-or-nothing filter would
        make that whole path undetectable."""
        self.assertEqual(
            self.candidates([FakePort("COM9", "Serial over Bluetooth link")]),
            ["COM9"])

    def test_result_is_ordered_by_device_name(self):
        self.assertEqual(
            self.candidates([FakePort("COM7", vid=1), FakePort("COM3", vid=1)]),
            ["COM3", "COM7"])


if __name__ == "__main__":
    unittest.main()
