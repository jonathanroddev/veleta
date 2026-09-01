# Hardware

What the product runs on, what is compatible, and what state each piece is
in. Step-by-step bring-up lives in
[`setup_wt901wifi.md`](setup_wt901wifi.md) and
[`setup_arduino_wifi.md`](setup_arduino_wifi.md).

## The kit (what is sold)

One assembled sensor for driving a camera or an object in Blender. One
sensor means a low entry price for the buyer and no soldering.

**v1 is the wired kit** (decided 2026-08-31): the sensor arrives on a USB
lead that carries its readings as well as its power. It is the path that is
proven from the board to the extension, and the only one whose PC-side
dependency (`pyserial`, pure Python) has nothing in it that has never run on
the buyer's operating system.

| Part | Model | Notes |
|---|---|---|
| Sensor | ATmega328P board + **MPU-6500**, USB lead | 6 axes, fusion in the core, 39 Hz measured |
| Software | core package + extension | Same version number, shipped together. The wired kit carries the `--wired-only` core build |
| Card | QR → short URL → installation guide | The URL is ours and redirects, so the destination can change without reprinting |

A **battery kit on BLE** and a **WiFi kit on the WT901WIFI** are both
prepared but are not what v1 leads with — see below and
[`packaging.md`](packaging.md).

## Compatible sensors

Anything that can emit the CSV layout in [`protocol.md`](protocol.md).
Today that means:

| Board / sensor | Profile | Rate | Fusion | State |
|---|---|---|---|---|
| WitMotion WT901WIFI | `fused` | up to 200 Hz | On the sensor | **Owned, never connected** |
| ESP32 + MPU-6050 | `raw6` | 100–200 Hz | In the core | Sketch written, **never flashed**, compile untested (no ESP core installed) |
| Arduino Nano/Uno + ESP-01 + MPU-6050 | `raw6` | ~20 Hz | In the core | Sketch written, **never flashed**; compiles for `arduino:avr:nano` (38% flash, 35% RAM) |
| Arduino Nano + MPU-6500, USB | 6 fields, no id | **39 Hz (measured)** | In the core | **Validated end to end on 2026-08-24. The v1 product path.** |
| ATmega328P + HM-10 (BLE) + MPU-6500 | 6 fields, no id | **40 Hz (measured)** | In the core | **Validated end to end on 2026-08-24.** The battery path, supported but not what v1 leads with |

`mpu_wifi_avr_esp01/` is named after the **architecture, not the board**.
It is board-agnostic 328P code: Nano by default, Uno with a different FQBN.
Do not fork it per board — the difference is a build flag, not code.

## The BLE path (the battery assembly)

For an assembly that runs on a **battery** the USB lead is power only and
cannot carry data, which is what BLE is for. It also rules WiFi out on
current draw for that assembly: an ESP-01 averages ~70 mA with 200-300 mA
peaks against the HM-10's ~8-10 mA, roughly a factor of ten.

Measured on 2026-08-24, and it costs nothing in rate: **39.7 Hz delivered
with 0.3% loss**, against 39.2 Hz on the cable. Setup and the full numbers
are in [`setup_ble_hm10.md`](setup_ble_hm10.md).

**This path was v1 until 2026-08-31 and is still fully supported.** What
moved it out of first place is the PC end, not the board: `bleak`'s WinRT
backend has never been exercised on Windows, so the cable ships first while
that stays true. Nothing here was removed, and the two open questions below
are still the ones to answer before a battery kit is sold.

> **The board, not the radio, is now the power problem.** An *original*
> Nano carries an FT232R USB-serial chip that draws ~15 mA whether or not
> USB is attached, plus a linear regulator that burns most of a 9 V
> battery as heat. That is more than the BLE module it feeds. A Pro Mini
> (same MCU, no USB chip) or an ESP32 is a different league for battery
> work. Not yet evaluated.

## The wired path

Arduino **Nano** (ATmega328P @ 16 MHz, 5 V), FQBN
`arduino:avr:nano:cpu=atmega328old` on the bench board, over USB serial with
an MPU-6500. **This is what v1 ships**, and it doubles as the bench: it is
the path with the fewest moving parts for checking a sensor, a sketch or a
filter change without a network or a radio in the way. A sold assembly is
not this bench board — see the power note above, which applies to anything
built on an original Nano — but it is the same sketch, the same CSV and the
same `SerialSource`.

> Nano clones normally ship the old bootloader: if upload fails with
> `not in sync`, use `arduino:avr:nano:cpu=atmega328old`. The bench Nano
> needs exactly that — it is an **original** board (FT232R, not a CH340
> clone) and its bootloader syncs at 57600, so plain `arduino:avr:nano`
> will not upload to it.

`firmware/wired/backups/` holds flash and EEPROM dumps of the **old Uno**
and, since 2026-08-24, of the bench **Nano** as it arrived (it carried the
stock AT-configuration passthrough sketch). They are gitignored — they
exist only on the machine that made them.

## What has never been done

Stated plainly, because everything downstream depends on it:

1. **The WT901WIFI has never been connected.** Neither the wired path nor
   the BLE one belongs on this list any more: on 2026-08-24 both were
   flashed and driven end to end — real CSV, real fusion, poses matching
   gravity to within 0.15 deg, and BLE agreeing with the cable to within
   0.3 deg on the same untouched board. The WiFi boards remain unflashed.
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

0. **Wired or BLE board?** Both are already brought up; steps 2 and 3 below
   are the UDP path and do not apply to either. For BLE follow
   [`setup_ble_hm10.md`](setup_ble_hm10.md). The list from here down is the
   **WiFi** bring-up, which is the one still undone.
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
