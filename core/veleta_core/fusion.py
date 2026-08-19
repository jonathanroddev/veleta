"""Complementary filter — the fusion that used to live inside Blender.

Unchanged in behaviour from the two bridges, with one deliberate
difference: `dt` is passed in instead of being read from `time.time()`
inside the filter. That is what makes it testable against a recording and
what lets file playback run faster or slower than real time without the
filter noticing.

Roll and pitch are absolute: the accelerometer gives them a gravity
reference. Yaw is integrated gyro ONLY and WILL drift, because an MPU-6050
has no magnetometer. Re-zero it with the core's `recenter` command.
"""

import math


class DeviceFusion:
    """Per-device filter state. One instance per DeviceID."""

    def __init__(self, alpha=0.98, bias_samples=50):
        self.alpha = float(alpha)
        self.bias_samples = int(bias_samples)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.bias = [0.0, 0.0, 0.0]
        self._bias_sum = [0.0, 0.0, 0.0]
        self._bias_n = 0
        self._seeded = False
        self.ready = False

    @property
    def bias_progress(self):
        """(samples collected, samples needed) — for user-facing messages."""
        return (self._bias_n, self.bias_samples)

    def update(self, accel, gyro, dt):
        """Feed one raw6 reading. Returns (roll, pitch, yaw) in degrees, or
        None while the gyro bias is still being estimated.

        KEEP THE SENSOR STILL for the first `bias_samples` frames: a bias
        left in place integrates straight into drift.
        """
        gx, gy, gz = gyro
        if not self.ready:
            self._bias_sum[0] += gx
            self._bias_sum[1] += gy
            self._bias_sum[2] += gz
            self._bias_n += 1
            if self._bias_n >= self.bias_samples:
                n = float(self._bias_n)
                self.bias = [s / n for s in self._bias_sum]
                self.ready = True
            return None

        gx -= self.bias[0]
        gy -= self.bias[1]
        gz -= self.bias[2]

        ax, ay, az = accel
        accel_roll = math.degrees(math.atan2(ay, az))
        accel_pitch = math.degrees(
            math.atan2(-ax, math.sqrt(ay * ay + az * az)))

        if not self._seeded:
            # Seed from the accelerometer instead of from 0, or the filter
            # spends its first second crawling from "flat" to the real
            # attitude.
            self.roll, self.pitch = accel_roll, accel_pitch
            self._seeded = True

        gyro_roll = self.roll + gx * dt
        gyro_pitch = self.pitch + gy * dt
        a = self.alpha
        self.roll = a * gyro_roll + (1 - a) * accel_roll
        self.pitch = a * gyro_pitch + (1 - a) * accel_pitch

        # Yaw: integrated gyro only. No magnetometer, so it drifts.
        self.yaw += gz * dt

        return (self.roll, self.pitch, self.yaw)
