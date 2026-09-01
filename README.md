# Veleta

**Motion sensors that drive a 3D scene in real time.** *Veleta* is Spanish
for the weather vane on a roof, whose only job is to tell you which way
something is pointing — exactly what this does: it reports orientation, not
position.

An IMU sensor streams its attitude to a small program on your machine; that
program fuses and zeroes it and re-exposes it over a documented protocol;
Blender picks it up and moves a camera or an object. One sensor today, a
capture suit later, and a Godot adapter after that.

> **Status: the cable path is validated on real hardware** (a Nano and an
> MPU-6500, 39 Hz, poses matching gravity to 0.15 deg) **and is what v1
> ships.** BLE is validated too and still supported, just no longer what
> the product leads with. **The extension has never been run inside
> Blender**, and no WiFi sensor has ever been connected. See
> [`docs/context.md`](docs/context.md#status).

## The three components

```
   sensor ───CSV───▶  core  ──JSON over UDP──▶  blender
  firmware/           core/                     blender/
   the board        a plain program             the extension

   the CSV arrives over a USB cable (v1), a BLE module, or WiFi;
   which one is a line in config, not a different program
```

| | What it does | Licence |
|---|---|---|
| [`firmware/`](firmware/) | Reads the IMU and emits the stream. Burned onto the microcontroller | **Proprietary** |
| [`core/`](core/) | Receives, fuses, calibrates, re-exposes over UDP. No Blender needed | **Proprietary** |
| [`blender/`](blender/) | Consumes the stream and applies it to the scene | **GPL v3 or later** |

## The licence map, and why it is not uniform

**Read this before assuming one licence covers the repository. It does
not.**

Blender's Python API is part of Blender, and Blender is GPL. So anything
that imports `bpy` and is published has to be GPL-compatible — the
extensions platform requires it in as many words. `blender/` is therefore
**GPL v3 or later**, and that is not negotiable.

`core/` and `firmware/` are **proprietary, all rights reserved**. Neither
imports `bpy`. The core is an independent program: it runs, and is useful,
with no Blender anywhere on the machine, and it talks to consumers over a
protocol documented in [`docs/protocol.md`](docs/protocol.md) — well enough
that anyone could write their own consumer without seeing a line of the
core. That is what keeps it out of the GPL's reach, and it is why the
protocol document is written for a stranger.

**The rule that holds it together:** the package uploaded to the extensions
platform contains **only the contents of `blender/`**. The core is never
distributed inside it. `scripts/build_extension.py` refuses to build a
package that breaks this.

The source in this repository being public is **not** a grant of licence to
the proprietary parts. See [`LICENSE`](LICENSE) and the `LICENSE` file in
each component.

## What the core computes

The three boxes above, zoomed in on the arithmetic. Every step is
trigonometry, a running sum or a weighted average; the numbers in brackets
are the sections of [`docs/math.md`](docs/math.md), which explains each one
in plain language.

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

Roll and pitch are absolute — gravity is their reference. **Yaw is
integrated gyroscope only and will drift**, because an MPU-6500 carries no
magnetometer; `recenter` is how it is cancelled. A `fused` sensor such as
the WT901WIFI does steps 1-4 on the chip and the core starts at step 5.

## Running it

The core, and a sensor if you have one:

```bash
cd core
python3 -m veleta_core --config config.wired.env    # a sensor on a USB cable
python3 -m veleta_core --config config.ble.env      # a BLE module
python3 -m veleta_core                              # listen on UDP 1399 (WiFi)
python3 -m veleta_core --play ../samples/wt901_desk_wobble.jsonl --loop
```

Each transport has its own configuration file because each sensor lays its
CSV out differently — the wired and BLE boards send six fields with no
device id, a WiFi WT901 sends more and names itself. **That is a
configuration difference, not a parser one**, which is why it is three
files and not three code paths. Using the wrong one has a single loud
symptom: every frame reported UNPARSED.

The `--play` line is the point of the recording mode: **the whole pipeline
— parsing, fusion, calibration — runs with no sensor attached.** It is the
fixture the tests run against, the way to reproduce a fault from a
recording a user sent without their hardware on your desk, and how you keep
working when the sensor is flat, broken or in another room. It also tells
apart "the sensor is broken" from "everything after it is broken", which is
otherwise a slow afternoon.

Then, in Blender, install the extension and press **Connect** in the
**Veleta** tab of the 3D viewport sidebar. Full walkthrough in
[`docs/installation.md`](docs/installation.md).

**With no kit at all** there is no core either — it ships with the
hardware — so the extension carries its own way of showing what it does: a
short recording travels inside the package and **Play demo** replays it
against your scene, with no core, no sensors and no network. That is what
somebody who installs from the extensions platform sees before they own
anything.

## The tests

Standard library only. No Blender, no hardware, under a second.

```bash
python3 -m unittest discover -s tests -t tests
```

They cover the quaternion math against independently constructed matrices,
frame parsing (including a deliberately reshuffled CSV layout, handled by
configuration alone), the complementary filter against attitudes it never
saw, gyro-bias removal, calibration, the core↔consumer protocol over real
sockets, and every recording in `samples/`.

## Layout

```
veleta/
├── firmware/     wired/ (Nano, USB serial) · ble/ (Nano+HM-10) · wifi/ (ESP32, Nano+ESP-01)
├── core/         veleta_core/ (the program) · tools/ (diagnostics, fake sensor)
├── blender/      the extension: manifest, panel, client, axis mapping, demo
├── docs/         protocol · math · context · hardware · installation · packaging
├── scripts/      build_extension.py · build_windows_bundle.py
├── samples/      recordings, for the demo and the tests
└── tests/        76 tests, standard library only
```

## Documentation

| | |
|---|---|
| [`docs/protocol.md`](docs/protocol.md) | Both wire formats and the recording format. The contract that makes the core an independent program |
| [`docs/math.md`](docs/math.md) | Every calculation the core makes, in the order a reading passes through it |
| [`docs/context.md`](docs/context.md) | Why the product is shaped like this, and what changed in the split |
| [`docs/hardware.md`](docs/hardware.md) | What is in the kit, what is compatible, what has never been tested |
| [`docs/installation.md`](docs/installation.md) | For the person who bought a kit |
| [`docs/packaging.md`](docs/packaging.md) | Versioning, reproducible builds, signing, distribution |
