# The math

Everything the core computes, in the order a reading passes through it.
Written to be read by someone who is not a control engineer, because the
whole of it is trigonometry, a running sum and a weighted average — the
only unfamiliar piece is the quaternion, and it earns its place for one
specific reason given in part 5.

Where this lives in the code: `core/veleta_core/fusion.py` (parts 2-4),
`core/veleta_core/quat.py` (part 5), `core/veleta_core/engine.py` (part 6),
`blender/axes.py` (part 7). Nothing here applies to a `fused` sensor, which
does its own fusion on the chip and hands the core finished angles; parts 5
onwards still apply to it.

---

## The flow

```
  the board · firmware/
  ─────────────────────
    accelerometer raw ──▶ / 16384 ──▶  ax ay az   [g]        (1)
    gyroscope     raw ──▶ / 131   ──▶  gx gy gz   [deg/s]
                                              │
                                              │  CSV, one line per reading
                                              ▼
  the core · core/veleta_core/
  ────────────────────────────
    ax ay az ─────── atan2 ─────────▶ accel_roll, accel_pitch     (2)
                                              │   where "down" is
    gx gy gz ── − bias ── + rate·dt ─▶ prediction                 (3, 4)
                                              │   how far it turned
                                              ▼
             0.98 · prediction  +  0.02 · accel_angles            (4)
                                              │   complementary filter
                                              ▼
                                  roll, pitch, yaw  [deg]
                                              │
                              from_euler_zyx  │                   (5)
                                              ▼
                                       q = (w, x, y, z)
                                              │
                                   offset · q │                   (6)
                                              │   zero = inverse of the pose held at calibration
                                              │  JSON, one pose per datagram
                                              ▼
  the consumer · blender/
  ───────────────────────
       signed permutation of (roll, pitch, yaw) ──▶ the scene     (7)
```

## The short version

**On the board** (part 1) — strip the chip's units:

```
accel[g] = raw / 16384          gyro[deg/s] = raw / 131
```

**The plumb line** (part 2). The accelerometer says which way gravity falls;
trigonometry turns that into two angles. The third does not exist here:
spinning about the vertical does not move gravity.

```
accel_roll  = atan2(ay, az)
accel_pitch = atan2(-ax, sqrt(ay*ay + az*az))
```

**The offset** (part 4). The first 50 samples with the sensor held still: their
mean *is* the gyroscope's error, because the truth at that moment is zero.
Subtract it from everything after.

```
bias = (1/N) * sum(gyro_i)        gyro = gyro - bias
```

**The fusion** (parts 3-4). A weighted average: the gyroscope is precise over short
intervals but drifts, gravity is reliable over long ones but lies the moment
you move. That 2% trickle erases the drift before it shows. The crossover is
~1.2 s at 40 Hz.

```
roll  = 0.98*(roll  + gx*dt) + 0.02*accel_roll
pitch = 0.98*(pitch + gy*dt) + 0.02*accel_pitch
yaw   = yaw + gz*dt                              <- uncorrected: it drifts
```

**To a quaternion** (part 5). Because angles cannot be added or subtracted
(rotations do not commute) and they jam at gimbal lock.

```
q = from_euler_zyx(roll, pitch, yaw)
```

**The zero** (part 6). Calibrating stores the inverse of the current pose; emitting
multiplies by it. "Undo where I was, apply where I am": what remains is the
rotation performed since. It is also what cancels the yaw drift.

```
offset = inverse(q_at_calibration)        q_emitted = offset * q_measured
```

**In Blender** (part 7). A signed permutation: the sign inverts a direction, the
permutation swaps axes, and neither does the other's job.

```
out[i] = sign * rpy[source_i]
```

---

## 1. What the sensor knows, and what it cannot

An MPU-6500 does not know its orientation. It measures two things, three
numbers each:

- **Accelerometer** — the force felt along each of its three axes. At rest
  the only force is gravity, so in practice it is **a plumb line**: it says
  which way is down, as seen from the sensor.
- **Gyroscope** — how fast it is turning about each axis. Not where it is;
  how fast it is moving right now.

Both arrive as raw integers. The firmware divides by the chip's two
sensitivity constants to get physical units, and that is all the math the
board does:

```
accel[g]    = raw / 16384      (ACCEL_SENS, at +/-2 g)
gyro[deg/s] = raw / 131        (GYRO_SENS,  at +/-250 deg/s)
```

## 2. Gravity to two angles

If you know where gravity points relative to the sensor, you know how it is
tilted. The accelerometer gives the three shadows of that arrow on the
sensor's axes; the ratios between them are the angle:

```
accel_roll  = atan2(ay, az)
accel_pitch = atan2(-ax, sqrt(ay*ay + az*az))
```

`atan2` is "given these two sides, give me the angle", in the form that
tells the four quadrants apart, so up is never confused with down. In pitch
the second argument is the combined length of the other two axes, which is
what keeps the result correct when the sensor is already tilted.

**The project's central limitation is born here.** Gravity gives two angles
and never three: spin the sensor about the vertical and the plumb line
points at exactly the same place. The accelerometer is blind to yaw. Without
a magnetometer there is no absolute reference for the third angle — roll and
pitch are absolute, yaw is not.

## 3. Gyroscope: summing rate to get position

The gyroscope reports degrees per second. To learn how far it has turned,
multiply by elapsed time and accumulate:

```
angle = angle + rate * dt
```

That is numerical integration, the simplest kind there is. It is excellent
over short intervals and very fast to react.

Its flaw is cumulative. Every sample carries a tiny error, and summing the
samples sums the errors too. When the error has a constant offset — the chip
reads 0.2 deg/s while sitting still — it **never cancels**: it grows in a
straight line. 0.2 deg/s of offset is 12 degrees of drift per minute.

`dt` is measured from arrival times and passed into the filter rather than
read from the clock inside it. That is what lets a recording be replayed
faster or slower than real time and still fuse to the same poses.

## 4. Removing the gyro offset, and the complementary filter

### The bias estimate

The filter opens with `GYRO_CALIB_SAMPLES` (50) readings during which it
emits nothing and the sensor must be held still. It sums them and divides by
50:

```
bias = (1/N) * sum(gyro_i)  for the first N samples
gyro = gyro - bias          for every sample thereafter
```

The mean of a still gyroscope **is** its offset, because the truth at that
moment is zero. It is the humblest step in the system and the one that
prevents the most drift; move during that half second and the contaminated
mean integrates for the rest of the session.

### The fusion

Two sources now describe the same thing with opposite flaws:

| | Short term | Long term |
|---|---|---|
| **Accelerometer** | Noisy, and any real movement is felt as force and mistaken for gravity | Reliable: gravity does not drift |
| **Gyroscope** | Smooth and precise | Drifts without bound |

The fusion is a weighted average, one line per axis:

```
roll  = a * (roll  + gx*dt) + (1-a) * accel_roll
pitch = a * (pitch + gy*dt) + (1-a) * accel_pitch
yaw   = yaw + gz*dt                                 (no correction available)

a = ALPHA_ROLL_PITCH = 0.98
```

98% of the result is "where I was, plus how far I turned"; 2% is "where the
plumb line says I am". It is called *complementary* because the weights sum
to one and each source covers exactly the other's blind spot: the gyroscope
owns fast movement, while that steady 2% trickle pulls the result back
towards true vertical before the drift becomes visible.

**What 0.98 means in seconds.** The crossover between the two sources is
roughly `a*dt/(1-a)`. At the ~40 Hz measured on the bench (`dt` = 0.025 s)
that is **about 1.2 seconds**: anything faster than a second is the
gyroscope's account of events, anything slower is settled by gravity.
Raising alpha moves the filter towards the pure gyroscope (smoother, more
drift); lowering it moves it towards the accelerometer (closer to vertical,
jumpier, more disturbed by real movement).

On the first usable sample the angles are **seeded** from the accelerometer
rather than from zero. Without that the filter would start out believing it
is flat and spend that same second-and-change crawling to the real attitude.

Yaw stays out of the average because there is nothing to correct it with.
That is what the `recenter` command is for.

### Two honest limits

Both follow from averaging angles as if they were ordinary numbers:

- Near +/-90 degrees of pitch the roll/pitch decomposition becomes
  ambiguous, and the weighted average misbehaves with it.
- Crossing +/-180 degrees of roll mixes 179 with -179 and drags the result
  backwards, because the gyro term accumulates unbounded while `atan2`
  returns a value in (-180, 180].

For a device whose job is to report which way something points, neither is
the normal case — but that is where the fence is.

## 5. Why quaternions

So far everything is three angles. Angles are comfortable to read and poor
to compute with:

- **They cannot be added or subtracted.** 90 degrees about X then 90 about Y
  is not the same as the reverse. Rotations do not commute, and the angle
  subtraction one reaches for by instinct is only ever an approximation, good
  for small rotations and wrong for large ones.
- **They jam.** At gimbal lock two of the three angles describe the same
  movement and a degree of freedom is lost.

A quaternion is another way of writing a rotation: four numbers
`(w, x, y, z)`. The intuition is *an axis and a turn about it* — the last
three point along the axis, the first encodes how far. The half angles in
`from_euler_zyx` are why: that halving is what turns composing rotations
into plain multiplication.

```
q = from_euler_zyx_degrees(roll, pitch, yaw)     # ZYX order: qx . qy . qz
```

The multiplication (`mul`, the Hamilton product) is the operation that
matters: **chaining two rotations is multiplying their quaternions**, with no
special cases, no jamming, and no size limit on the turn. `conjugate` — flip
the sign of the last three — undoes a rotation. Order is fixed and
documented: `mul(a, b)` means "apply b, then a", read like a matrix product.
The Euler order is **ZYX**, which is WitMotion's convention and what the
earlier Blender bridges asked `mathutils` for.

## 6. Zeroing: a multiplication, not a subtraction

`calibrate()` and `recenter()` store the inverse of the pose held at that
moment, and every pose after it is multiplied by that:

```
offset    = inverse(q_at_calibration)      # conjugate of the unit quaternion
q_emitted = offset * q_measured
```

Read it as *undo the pose I was in when zeroed, then apply the current one*.
Stand still and the two cancel to the identity — absolute zero. Move, and
what remains is exactly the rotation performed since calibration, which is
what the scene should receive.

This is where the quaternion pays for itself in a way you can see on screen:
subtracting three angles only approximates this, and fails visibly as soon as
tilt and yaw are combined. The multiplication is exact at any attitude. And
because yaw can only ever drift, this same mechanism is what cancels it —
recentring declares the current attitude to be the new zero.

## 7. Axis mapping, on the consumer's side

The core emits orientation in the sensor's own frame and stops there:
Blender is Z-up, Godot is Y-up, and no single convention serves both.
`blender/axes.py` does the adaptation, and it is the simplest math in the
project — **a signed permutation**:

```
out[i] = sign_i * SIGN_source * rpy[source_i]     for i in X, Y, Z
```

- A **sign** inverts a direction: the object turns the wrong way.
- A **permutation** swaps axes: you move one axis on the sensor and a
  different one responds. No combination of signs can do that, which is why
  the two are separate settings.

Formally it is a multiplication by a signed permutation matrix; in the code
it is written as what it is. Note the order: the axis map is applied **after**
the calibration offset, unlike the pre-split bridges. See the known
differences in `context.md`.

---

## In one line

Trigonometry turns gravity into the vertical, integration turns rate into
movement, a 98/2 weighted average takes the best of each, quaternions
compose and cancel rotations without the traps of Euler angles, and zero is
not subtracted — it is multiplied by the inverse.
