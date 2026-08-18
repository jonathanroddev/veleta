# Hardware

What the product runs on, what is compatible, and what state each piece is
in. Step-by-step bring-up lives in
[`setup_wt901wifi.md`](setup_wt901wifi.md) and
[`setup_arduino_wifi.md`](setup_arduino_wifi.md).

## The kit (what is sold)

One assembled sensor, WiFi, for driving a camera or an object in Blender.
One sensor means a low entry price for the buyer and no soldering.

| Part | Model | Notes |
|---|---|---|
| Sensor | WitMotion **WT901WIFI** | 9 axes, Kalman fusion on board, absolute heading, UDP/TCP streaming, up to 200 Hz |
| Software | core installer + extension | Same version number, shipped together |
| Card | QR → short URL → installation guide | The URL is ours and redirects, so the destination can change without reprinting |

## Compatible sensors

Anything that can emit the CSV layout in [`protocol.md`](protocol.md).
Today that means:

| Board / sensor | Profile | Rate | Fusion | State |
|---|---|---|---|---|
| WitMotion WT901WIFI | `fused` | up to 200 Hz | On the sensor | **Owned, never connected** |
| ESP32 + MPU-6050 | `raw6` | 100–200 Hz | In the core | Sketch written, **never flashed**, compile untested (no ESP core installed) |
| Arduino Nano/Uno + ESP-01 + MPU-6050 | `raw6` | ~20 Hz | In the core | Sketch written, **never flashed**; compiles for `arduino:avr:nano` (38% flash, 35% RAM) |
| Arduino Nano + MPU-6050, USB | 6 fields, no id | ~50 Hz | In the core | Bench. Validated to raw CSV **on the old Uno** |

`mpu_wifi_avr_esp01/` is named after the **architecture, not the board**.
It is board-agnostic 328P code: Nano by default, Uno with a different FQBN.
Do not fork it per board — the difference is a build flag, not code.

## The wired bench

Arduino **Nano** (ATmega328P @ 16 MHz, 5 V), FQBN `arduino:avr:nano`, over
USB serial with an MPU-6050. It is not part of the kit and is not sold: it
is the path with the fewest moving parts for checking a sensor, a sketch or
a filter change without a network in the way.

> Nano clones normally ship the old bootloader: if upload fails with
> `not in sync`, use `arduino:avr:nano:cpu=atmega328old`.

`firmware/wired/backups/` holds flash and EEPROM dumps of the **old Uno**,
not of the Nano. They are gitignored — they exist only on the machine that
made them.

## What has never been done

Stated plainly, because everything downstream depends on it:

1. **No sensor has ever been connected.** Not the WT901WIFI, not a flashed
   board.
2. **Nothing has ever driven an object inside Blender.** There is no
   Blender on the development machine.
3. **The WT901WIFI's real CSV layout is unconfirmed.** `IDX_ANGLE_X/Y/Z=7,8,9`
   and `IDX_DEVICE=0` come from the product documentation and may vary with
   firmware. Confirm with `core/tools/read_udp.py`, then adjust
   `core/config.env` — never the parser.
4. **No axis mapping is validated.** It cannot be until a sensor is
   physically mounted on something. That is why the defaults are identity.
5. **The Nano + ESP-01 rate is an estimate** from the AT round trip at 9600
   baud. Measure it before designing around it.

## Bring-up order, with hardware in hand

1. Flash one board — **ESP32 first if you have one**, it has far fewer ways
   to fail.
2. `python3 core/tools/read_udp.py 1399 10` → confirm frames arrive, the
   field count and the DeviceID.
3. Start the core, connect from Blender, calibrate in the reference pose.
4. Tune the axis map and signs until the object follows faithfully.
5. Several sensors: `devices` → fill the sensor→object map.
6. **Armature**: move from loose objects to `pose.bones[...]`, resolving
   each bone's orientation relative to its parent. That is the heart of the
   suit and the real remaining work.
