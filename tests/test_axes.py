"""The extension's axis mapping.

Lives on the consumer side because Blender is Z-up and Godot is Y-up, and
imports no `bpy`, which is exactly why it can be tested here.
"""

import unittest

import context
import axes


class TestAxisMap(unittest.TestCase):
    def test_identity(self):
        mapping, warning = axes.parse_axis_map("roll,pitch,yaw")
        self.assertIsNone(warning)
        self.assertEqual(axes.remap((10, 20, 30), mapping), (10, 20, 30))

    def test_permutation_is_what_fixes_cross_axis_coupling(self):
        """'I rotate one axis and another one responds' is never a sign."""
        mapping, _ = axes.parse_axis_map("pitch,roll,yaw")
        self.assertEqual(axes.remap((10, 20, 30), mapping), (20, 10, 30))

    def test_inversion_prefix(self):
        mapping, _ = axes.parse_axis_map("roll,pitch,-yaw")
        self.assertEqual(axes.remap((10, 20, 30), mapping), (10, 20, -30))

    def test_signs_and_permutation_combine_in_order(self):
        mapping, _ = axes.parse_axis_map("-pitch,roll,yaw")
        got = axes.remap((10, 20, 30), mapping, signs=(1.0, -1.0, 1.0))
        self.assertEqual(got, (20, 10, 30))

    def test_a_sign_cannot_do_a_permutation(self):
        """The reason both knobs exist, stated as a test."""
        swap, _ = axes.parse_axis_map("pitch,roll,yaw")
        identity, _ = axes.parse_axis_map("roll,pitch,yaw")
        for signs in ((1, 1, 1), (-1, 1, 1), (1, -1, 1), (-1, -1, -1)):
            self.assertNotEqual(axes.remap((10, 20, 30), identity, signs),
                                axes.remap((10, 20, 30), swap))

    def test_bad_specs_warn_and_fall_back_to_identity(self):
        for spec in ("roll,pitch", "roll,pitch,yaw,extra", "x,y,z", ""):
            with self.subTest(spec=spec):
                mapping, warning = axes.parse_axis_map(spec)
                self.assertIsNotNone(warning, "a bad spec must say so")
                self.assertEqual(list(mapping), list(axes.IDENTITY))

    def test_a_repeated_source_is_applied_but_flagged(self):
        mapping, warning = axes.parse_axis_map("roll,roll,yaw")
        self.assertIsNotNone(warning)
        self.assertEqual(axes.remap((10, 20, 30), mapping), (10, 10, 30))


if __name__ == "__main__":
    unittest.main()
