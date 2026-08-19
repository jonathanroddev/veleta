"""Quaternion math, checked against an independently built matrix.

The core cannot use `mathutils`, so this replaces it. The composition order
is the part worth pinning down: ZYX means Z is applied first, which
composes as R = Rx . Ry . Rz.
"""

import math
import unittest

import context
from veleta_core import quat


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def matmul(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3))


class TestQuaternion(unittest.TestCase):
    ANGLES = [(0, 0, 0), (10, 20, 30), (-45, 5, 170), (90, 0, -90),
              (12.5, -33.25, 4)]

    def test_euler_round_trip(self):
        for a in self.ANGLES:
            with self.subTest(angles=a):
                q = quat.from_euler_zyx_degrees(*a)
                back = quat.to_euler_zyx_degrees(q)
                for got, want in zip(back, a):
                    self.assertAlmostEqual(got, want, places=6)

    def test_composition_matches_matrices(self):
        """from_euler_zyx must equal Rx . Ry . Rz, built independently."""
        for a in self.ANGLES:
            with self.subTest(angles=a):
                rx, ry, rz = (math.radians(v) for v in a)
                expected = matmul(matmul(rot_x(rx), rot_y(ry)), rot_z(rz))
                got = quat.to_matrix(quat.from_euler_zyx_degrees(*a))
                for i in range(3):
                    for j in range(3):
                        self.assertAlmostEqual(got[i][j], expected[i][j],
                                               places=9)

    def test_inverse_cancels(self):
        q = quat.from_euler_zyx_degrees(31, -12, 88)
        identity = quat.mul(quat.inverse(q), q)
        self.assertAlmostEqual(abs(identity[0]), 1.0, places=9)
        for c in identity[1:]:
            self.assertAlmostEqual(c, 0.0, places=9)

    def test_multiplication_is_ordered(self):
        """mul(a, b) applies b first: it must match the matrix product."""
        a = quat.from_euler_zyx_degrees(20, 0, 0)
        b = quat.from_euler_zyx_degrees(0, 35, 0)
        got = quat.to_matrix(quat.mul(a, b))
        expected = matmul(quat.to_matrix(a), quat.to_matrix(b))
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(got[i][j], expected[i][j], places=9)

    def test_normalize_survives_garbage(self):
        self.assertEqual(quat.normalize((0, 0, 0, 0)), quat.IDENTITY)


if __name__ == "__main__":
    unittest.main()
