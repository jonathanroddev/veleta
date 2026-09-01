# Context: why the product is shaped like this

Decisions and the reasoning behind them. Hardware specifics are in
[`hardware.md`](hardware.md), the wire formats in
[`protocol.md`](protocol.md).

## Goal

Capture orientation (roll/pitch/yaw) from IMU sensors and apply it in real
time to a 3D scene. Position is **out of scope**: recovering it would mean
double-integrating acceleration, whose drift is unacceptable without an
external reference.

The first sellable product is **one sensor** driving a camera or an object
in Blender. The multi-sensor capture suit is the ambition, not the v1 —
which is why the core treats "several sensors" as the normal case even
though only one is sold at first.

## Three components, and why they are separate

| | What it does | Licence |
|---|---|---|
| `firmware/` | Reads the IMU and emits the stream | Proprietary |
| `core/` | Receives, fuses, calibrates, re-exposes over UDP | Proprietary |
| `blender/` | Consumes the stream and applies it to the scene | GPL v3 or later |

Blender's Python API is part of Blender and Blender is GPL, so anything
that imports `bpy` and is published has to be GPL-compatible. The
extensions platform requires it explicitly too. The core does **not**
import `bpy`: it is an independent program, useful with no Blender on the
machine, that communicates over a documented protocol. That is what keeps
it outside the GPL — and the reason `protocol.md` is written for a stranger
rather than as a note to self.

**The rule that must not be broken:** the package uploaded to the
extensions platform contains **only the contents of `blender/`**.
`scripts/build_extension.py` enforces it and fails the build otherwise.

## The three hardware paths

| | wired | ble | wifi |
|---|---|---|---|
| Transport | USB serial, 115200 baud | HM-10, 38400, one notify characteristic | UDP over 2.4 GHz WiFi |
| Frame | `ax,ay,az,gx,gy,gz` (no id — the link *is* the id) | the same six fields (id is the advertised BLE name) | `deviceId,...` |
| Fusion | In the core | In the core | In the core for `raw6`; in the sensor for the WT901WIFI |
| Multi-sensor | No | One peripheral per connection | Native: one socket, routed by DeviceID |
| Dependencies | `pyserial`, in the core only | `bleak`, in the core only | None |
| Measured rate | **39 Hz** | **39.7 Hz, 0.3% loss** | never connected |
| Role | **The v1 kit**, and the bench | The battery assembly | Where multi-sensor goes |

The wired and WiFi paths used to be two separate programs. All three are now
**sources** of one core, which is why they share the fusion, the calibration
and the protocol instead of a family resemblance.

A classic Bluetooth module is not a fourth path: it presents itself as a
virtual COM port, so it is the wired one over the air, with no new code.

> **Why the cable leads v1** (decided 2026-08-31, reversing 2026-08-24).
> BLE is the better assembly — a battery needs it, and it measures
> marginally faster — but its PC end rests on `bleak`, whose WinRT backend
> has still never run on a Windows machine. `pyserial` is pure Python and
> has no such unknown. The cable is therefore what ships first; nothing
> about BLE was removed, and `--wired-only` exists so the shipped package
> does not even carry the untested half.

## Decisions

### 1. Fusion in the core, not on the board
The boards only read the IMU and send raw values. The filter can then be
iterated without reflashing anything — and with a suit, without reflashing
*N* boards. The WT901WIFI is the exception: it fuses internally with its
own Kalman filter and offers no raw-only mode, so its angles are taken as
given.

### 2. Complementary filter, not Madgwick/Mahony
Simpler to understand and debug, which matters more than optimality in a
first version. It can be swapped for a 6-axis Madgwick if fast turns turn
out to look unstable — and now that it lives in the core with tests around
it, swapping it is a contained job.

### 3. Yaw drift is accepted on MPU-6050 hardware
The MPU-6050 has **no magnetometer**, so yaw has no absolute reference: it
is integrated gyro and drifts. Mitigated by estimating the gyro bias at
startup (the sensor must be still) and by re-zeroing on demand. The
WT901WIFI does not have this problem (9 axes, absolute heading).

### 4. UDP, never TCP
Lower latency, and a lost packet is simply dropped in favour of the next
one. TCP would retransmit an already-stale pose and deliver it late, which
is worse than not delivering it.

### 5. Sensor ranges written explicitly in every sketch
The MPU-6050 clone in this project did **not** boot in the default ±2g
range (it read ~0.27g at rest instead of ~1g). Every sketch writes
`ACCEL_CONFIG` (0x1C) and `GYRO_CONFIG` (0x1B) explicitly rather than
trusting defaults.

### 6. Axis mapping is configuration, and it lives in the consumer
How a sensor is mounted decides which of its axes drives which scene axis.
Two knobs, applied in order: `SIGN_*` inverts the **direction** of a
source; `AXIS_MAP` **permutes** which source drives X, Y and Z. Signs
cannot fix a permutation, which is why both exist — "I move one axis and
*another* one responds" is always `AXIS_MAP`.

They sit in the **extension's preferences**, not in the core, because
Blender is Z-up and Godot is Y-up: there is no mapping that serves both, so
the core stays engine-agnostic and each consumer maps for itself.

### 7. Calibration is a reference pose, in quaternions
The core captures each sensor's current orientation as its zero and applies
the inverse to every reading. Quaternions, so no gimbal lock, all three
axes at once, and one uniform procedure for every sensor of a suit: strike
the pose, press Calibrate.

### 8. Frame indices are configuration
Firmware revisions shuffle CSV layouts. The core addresses fields through
`IDX_*` in `config.env`. A layout difference is **never** fixed by patching
the parser, and `tests/test_frames.py` pins that down with a reshuffled
layout it handles by configuration alone.

### 9. Subscription, not a configured destination
See [`protocol.md`](protocol.md#why-subscription-and-not-a-configured-destination).

### 10. The extension configures itself in Blender, not in `config.env`
The core keeps the project's `config.env` convention: KEY=value, no
dependency to read it. The extension cannot — an installed extension's
files are replaced on update, so a config file inside the package is a file
the user edits and then loses. It uses Blender's own preferences, which is
also where an artist expects to find them.

## Why the extension is a package now, not one loose file

The old bridges were each a single self-contained `.py`, and deliberately
so: a script in Blender's text editor often has no `__file__`, so every
extra import was another way to break on a machine you are not sitting at.
The duplication between them was the accepted price.

That decision has now been overtaken, exactly as it said it would be — it
ended with "if the duplication ever stops being bounded, the answer is a
proper Blender add-on, not a loose package next to the script." Becoming an
extension **is** that moment: an extension is installed as a package, its
imports are package-relative and always resolve, and there is no text
editor involved. The self-contained-file rule does not apply here and
should not be reintroduced.

## Known differences from the pre-split behaviour

Worth reading before blaming the hardware for something.

1. **The axis map is applied after the calibration offset**, where it used
   to be applied before. The core zeroes in the sensor's frame and the
   consumer maps the result. These are not equivalent in general: a
   permutation of Euler angles is not a rotation conjugation. The order is
   arguably better — you cancel the mounting offset first and then fix the
   axis convention on a rotation that sits near identity — but **it is a
   change, and neither order has ever been validated against a real
   mounting.** Re-tune `AXIS_MAP` when the hardware is in hand, and do not
   copy values from the old `config.env` files expecting the same result.

2. **`dt` is passed into the filter** instead of read from the clock
   inside it. Live behaviour is unchanged; playback no longer depends on
   the wall clock, which is what makes the filter testable.

3. **The wired path no longer zeroes Euler angles** (`recenter_yaw`,
   `recenter_all`). It uses the same quaternion reference pose as
   everything else. One procedure for every sensor and every transport.

4. **`pyserial` is out of Blender.** It is an optional dependency of the
   core, imported only when the serial source is used. Nothing has to be
   installed into Blender's bundled Python any more.

## How this is validated without hardware

`core/tools/fake_sensor.py` emits UDP frames that are physically
consistent: the accelerometer carries gravity projected onto the simulated
attitude and the gyro carries its derivative. Feeding them through the
filter therefore has to return the attitude that generated them, which
makes it a fixture rather than a traffic generator.

`tests/` (76 tests, standard library only, no Blender needed) covers the
quaternion math against independently built matrices, frame parsing
including a deliberately reshuffled layout, the filter against attitudes it
did not see, bias removal, calibration, the protocol over real sockets, and
every recording in `samples/`.

```bash
python3 -m unittest discover -s tests -t tests
```

## Status

- **Software:** validated end to end without hardware. Sensors → core →
  subscriber works with two profiles at once, recording and playback work,
  the extension package builds reproducibly.
- **The extension inside Blender: never run.** There is no Blender on the
  development machine. The parts that do not need it (`client.py`,
  `axes.py`) are tested; the parts that do (`__init__.py`, the manifest,
  the panel) are written but unexecuted. Validate with
  `blender --command extension validate` before anything else.
- **Hardware: the wired and BLE boards are validated** (2026-08-24). Both
  were flashed and driven end to end: real CSV, real fusion, poses matching
  gravity to 0.15 deg, BLE agreeing with the cable to 0.3 deg. **The wired
  path is what v1 ships** (2026-08-31). **No WiFi sensor has ever been
  connected** and those sketches remain unflashed. See
  [`hardware.md`](hardware.md).
- **Windows: the core package has started once** (2026-08-27), far enough
  to prove the bundled interpreter finds the core. The radio has never been
  touched from Windows, which is the reason the cable leads v1.
