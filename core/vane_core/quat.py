"""Minimal quaternion math.

The Blender bridges used `mathutils`, which ships with Blender and only
exists inside it. The core is a standalone process, so it carries its own
implementation: about sixty lines, standard library only, and testable
without Blender.

CONVENTION
    A quaternion is a plain tuple (w, x, y, z), unit norm, and rotations
    compose left to right the same way matrices do: `mul(a, b)` is "apply b,
    then a", exactly like the matrix product A @ B.

    Euler angles use the **ZYX** order, which is what WitMotion uses to
    define attitude and what the previous Blender bridges asked mathutils
    for (`Euler(..., 'ZYX')`). In that order the rotation is applied about Z
    first, then Y, then X, which composes as R = Rx . Ry . Rz.
"""

import math

IDENTITY = (1.0, 0.0, 0.0, 0.0)


def mul(a, b):
    """Hamilton product. `mul(a, b)` applies b first, then a."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def conjugate(q):
    """Conjugate. For a unit quaternion this is also its inverse."""
    w, x, y, z = q
    return (w, -x, -y, -z)


def normalize(q):
    """Return q scaled to unit norm; identity if it is degenerate."""
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n < 1e-12:
        return IDENTITY
    return (w / n, x / n, y / n, z / n)


def inverse(q):
    """Inverse of a rotation quaternion (normalized first, to be safe)."""
    return conjugate(normalize(q))


def from_euler_zyx(rx, ry, rz):
    """Build a quaternion from ZYX Euler angles, in RADIANS.

    `rx`/`ry`/`rz` are the rotations about X, Y and Z. The ZYX order means
    Z is applied first, so the composition is qx . qy . qz.
    """
    cx, sx = math.cos(rx * 0.5), math.sin(rx * 0.5)
    cy, sy = math.cos(ry * 0.5), math.sin(ry * 0.5)
    cz, sz = math.cos(rz * 0.5), math.sin(rz * 0.5)
    qx = (cx, sx, 0.0, 0.0)
    qy = (cy, 0.0, sy, 0.0)
    qz = (cz, 0.0, 0.0, sz)
    return mul(mul(qx, qy), qz)


def from_euler_zyx_degrees(roll, pitch, yaw):
    """Same as `from_euler_zyx` but taking degrees, which is what the
    sensors and the complementary filter speak."""
    return from_euler_zyx(math.radians(roll), math.radians(pitch),
                          math.radians(yaw))


def to_euler_zyx(q):
    """Decompose into ZYX Euler angles (rx, ry, rz) in RADIANS.

    Inverse of `from_euler_zyx`. At |pitch| = 90 degrees the decomposition
    is degenerate (gimbal lock): there the Z rotation is folded into X, the
    usual convention. Nothing downstream depends on this being unique, it
    is used for diagnostics and for the consumer-side axis mapping.
    """
    w, x, y, z = normalize(q)
    # R = Rx . Ry . Rz, so sin(ry) sits at row 0 / column 2 of the matrix.
    sy = 2.0 * (x * z + w * y)
    sy = max(-1.0, min(1.0, sy))
    ry = math.asin(sy)
    if abs(sy) > 0.99999:  # gimbal lock: X and Z are no longer separable
        rx = math.atan2(-2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + z * z))
        rz = 0.0
    else:
        rx = math.atan2(-2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + y * y))
        rz = math.atan2(-2.0 * (x * y - w * z), 1.0 - 2.0 * (y * y + z * z))
    return (rx, ry, rz)


def to_euler_zyx_degrees(q):
    """`to_euler_zyx` in degrees."""
    return tuple(math.degrees(a) for a in to_euler_zyx(q))


def to_matrix(q):
    """3x3 rotation matrix as a tuple of rows. Used by the tests to check
    the quaternion composition against an independent construction."""
    w, x, y, z = normalize(q)
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
        (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
        (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)),
    )
