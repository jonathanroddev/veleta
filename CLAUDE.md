# Guide for Claude Code — veleta

Read [`docs/context.md`](docs/context.md) for the decisions and
[`docs/protocol.md`](docs/protocol.md) for the wire formats before changing
anything that touches parsing, transport or licensing.

## What this is

Three components, and the separation between them is a **licence
boundary**, not a preference:

- `firmware/` — reads the IMU, emits CSV. **Proprietary.**
- `core/` — fuses, calibrates, re-exposes over UDP. Imports no `bpy`.
  **Proprietary.**
- `blender/` — consumes the stream, drives the scene. **GPL v3 or later.**

## Rules that are not stylistic

- **Never let `core/` import `bpy`,** and never let `blender/` import from
  `core/`. The moment either happens, the licence separation is gone. The
  two talk over the documented protocol and nothing else.
- **Only `blender/` goes into the extension package.**
  `scripts/build_extension.py` enforces this and must keep doing so.
- **Firmware, core and extension share one version number.** `VERSION` at
  the root is the source; `tests/test_version.py` fails when the three
  copies drift.

## Rules of the code

- **A different CSV layout is a configuration change**, never a parser
  change: that is what `IDX_*` in `core/config.env` is for. Three configs
  ship: `config.env` (WiFi, 7 fields), `config.wired.env` and
  `config.ble.env` (6 fields, no DeviceID).
- **Never out-run a link.** On BLE, over-running does not drop whole
  frames: the HM-10 drops bytes mid-line and the debris still parses as
  six numeric fields. Emitters are paced below a *measured* ceiling, and
  `TX_PERIOD_MS` is a safety limit, not a tuning knob.
- **A wrong-looking axis is a configuration change**, never a code change:
  that is what the extension's `AXIS_MAP` and `SIGN_*` are for. Axis
  mapping lives on the **consumer** side — Blender is Z-up, Godot is Y-up.
- **The core's configuration is `config.env`**, read with no external
  dependency. **The extension's configuration is Blender preferences** — an
  installed extension's files are replaced on update, so a config file
  inside the package is one the user edits and then loses.
- **Network credentials go in `firmware/*/secrets.h`** (gitignored, one per
  board). Never commit an SSID, a password or a LAN IP.
- **Blender code must not block the interface:** `bpy.app.timers`.
- **Standard library only**, with two justified exceptions, both in the
  core and both imported lazily so only the transport that needs them
  pays: `pyserial` for the wired bench, `bleak` for BLE. Justify anything
  new. Note `bleak` is not pure Python like `pyserial` — it wraps a
  compiled platform backend (pyobjc / WinRT / D-Bus), so the Windows
  bundle ships it as eleven pinned wheels built for that exact
  interpreter, and each one is a thing that can only first be exercised on
  Windows. Read the BLE section of `scripts/build_windows_bundle.py`
  before touching that list: what a wheel *declares* it needs is not what
  it needs — `winrt-runtime` imports `typing_extensions` unconditionally
  and says so nowhere bleak's metadata can be read for it.
- **Code, comments and user-facing messages in English.** Spanish is for
  the customer-facing site and its installation guide, not for the
  repository.
- **The built-in demo is a demo, not a second core.** `blender/playback.py`
  replays a bundled recording of already-fused angles so the extension does
  something for someone with no kit. It must never grow fusion, calibration
  or device routing — that is the core's work, and duplicating it across
  the licence boundary is exactly what the split exists to prevent.
- **The extension is a package, not a loose script.** The old
  "one self-contained file" rule was about Blender's text editor, where
  `__file__` often does not exist. It does not apply to an installed
  extension — do not reintroduce it.

## Current status

- **Software:** validated end to end without hardware. Two sensor profiles
  at once, recording and playback, reproducible extension build.
  `python3 -m unittest discover -s tests -t tests` → 76 tests, under a
  second, no Blender and no hardware needed.
- **The extension has never run inside Blender.** There is none on this
  machine. `client.py` and `axes.py` are tested; `__init__.py`, the
  manifest and the panel are written but unexecuted. First job on a machine
  with Blender: `blender --command extension validate dist/veleta-<v>.zip`.
- **The BLE path is the product path and is validated on real hardware**
  (2026-08-24): ATmega328P + HM-10 + MPU-6500, 39.7 Hz delivered, 0.3%
  loss, poses agreeing with the cable to 0.3 deg. The final assembly runs
  on a battery, so USB is power only. Run it with
  `python3 -m veleta_core --config config.ble.env`.
- **The wired bench is validated on real hardware** (2026-08-24): a Nano
  flashed with `mpu_serial_bridge`, an MPU-6500 at I2C 0x68, 39 Hz measured,
  fused poses matching gravity to within 0.15 deg. Run it with
  `python3 -m veleta_core --config config.wired.env` — the default
  `config.env` carries the WiFi layout and rejects both 6-field paths.
- **No WiFi sensor has ever been connected.** The WT901WIFI is owned but
  unconnected; the AVR WiFi sketch compiles (`arduino:avr:nano`, 38% flash /
  35% RAM), the ESP32 one is compile-untested.
- **The Windows core package has started on Windows once** (2026-08-27,
  the partner's machine). The bundled `python.exe` runs and finds the
  core: that much is settled. The run itself died in `import bleak` on a
  missing `typing_extensions`, now shipped — so **the radio has still
  never been touched from Windows**, and `bleak`'s WinRT backend remains
  the least-proven half of the product. It is unsigned on purpose — a test
  build, not a customer one. See `docs/packaging.md`.
- The recording in `samples/` is **synthetic**, from `fake_sensor.py`.

## Known uncertainties (resolve with hardware in hand)

1. **The WT901WIFI's real CSV layout.** `IDX_ANGLE_X/Y/Z=7,8,9` and
   `IDX_DEVICE=0` come from the product documentation and may vary with
   firmware. Confirm with `core/tools/read_udp.py`, adjust `config.env`.
2. **Axis frames.** Nothing is validated against a real mounting; the
   defaults are identity precisely because it is unknown. Note that the
   axis map is now applied **after** the calibration offset, where it used
   to be applied before — see "known differences" in `docs/context.md`.
   Do not copy old `AXIS_MAP` values expecting the same result.
3. **The Nano + ESP-01 rate.** ~20 Hz is an estimate from the AT round trip
   at 9600 baud. Measure it with `read_udp.py` before designing around it.
   For reference, the wired path measured 39 Hz where the docs had estimated
   50 — estimates here have run optimistic.

## Testing without hardware

```bash
python3 -m unittest discover -s tests -t tests     # the suite

cd core
python3 -m veleta_core --play ../samples/wt901_desk_wobble.jsonl --loop
# ...or a live fake sensor, in two terminals:
python3 -m veleta_core
python3 tools/fake_sensor.py 1399 0 50 127.0.0.1 WT53abc
python3 tools/fake_sensor.py 1399 0 20 127.0.0.1 ESP32_A raw6
```

`fake_sensor.py` is physically consistent — gravity projected onto the
simulated attitude, gyro as its derivative — so the fusion can be checked
against the attitude that generated it. When a real sensor shows a
different layout than the emitter, **the emitter is not wrong**: it
reproduces the documented default. Adjust `IDX_*` in `core/config.env`.

## What is deliberately not here

- `godot/` — it comes when it comes. The protocol is what makes it a matter
  of writing a consumer rather than extending the core.
- Wireless multi-sensor support and the armature work. See
  `docs/hardware.md` for the bring-up order.
