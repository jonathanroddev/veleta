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
- **One core package per sensor path, never a combined one** (decided
  2026-09-03). A customer buys one kit, so the folder they open holds one
  launcher, one settings file and a README about the hardware in their box.
  `--path` selects; there is nothing that produces a mixture. Only `cable`
  builds today — Bluetooth and WiFi each need their own README first, and
  the build refuses and says so. **The buyer's guide ships beside the zips,
  never inside one:** it is read before anything is unzipped.
- **Firmware, core and extension share one version number.** `VERSION` at
  the root is the source; `tests/test_version.py` fails when the four
  copies drift — the core, the manifest, the extension module, and **every
  sketch in `firmware/`**, which prints `# veleta <sketch> <version>` once
  at boot. The banner carries no comma, so a core reading that stream drops
  it for having fewer than `MIN_FIELDS` fields. Bump `VERSION` and the
  sketches go with it.

## Rules of the code

- **A different CSV layout is a configuration change**, never a parser
  change: that is what `IDX_*` in `core/config.env` is for. Four configs
  ship: `config.env` (WiFi, 7 fields), `config.wired.env` and
  `config.ble.env` (6 fields, no DeviceID), and `config.demo.env` (the
  bundled recording's layout). **Every shipped launcher names its config**
  — a path that relies on the built-in defaults instead is one that breaks
  silently the day the defaults move, and since the Windows package renames
  these files (`ajustes-sensor.txt` and friends, `PACKAGE_NAMES` in
  `scripts/build_windows_bundle.py`) the search-order fallback no longer
  finds anything there at all. Repository names are English; the package is
  what the buyer double-clicks. See `docs/packaging.md`.
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
  repository. The **one** exception inside the repo is
  `packaging/windows/guia-instalacion-es.html` and the
  `Guia-de-instalacion.pdf` rendered from it, which ship inside the wired
  package because they are what the buyer reads. Do not translate them,
  and re-render the PDF after editing the HTML — `--check` fails when the
  PDF is the older of the two. Command in `docs/packaging.md`.
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
  `python3 -m unittest discover -s tests -t tests` → 91 tests, under a
  second, no Blender and no hardware needed.
- **The extension has now run inside Blender, once** (reported
  2026-09-02, the partner's Windows machine): it installed, connected to
  the core and drove an object. Before that, `__init__.py`, the manifest
  and the panel were written but unexecuted — `client.py` and `axes.py` are
  the parts under test. There is still no Blender on this machine, so it
  remains unexercised here, and
  `blender --command extension validate dist/veleta-extension-blender-<v>.zip`
  has never been run. See `docs/fieldnotes.md` — that same session left one
  open fault.
- **The wired path is the product path** (decided 2026-08-31) **and is
  validated on real hardware** (2026-08-24): a Nano flashed with
  `mpu_serial_bridge`, an MPU-6500 at I2C 0x68, 39 Hz measured, fused poses
  matching gravity to within 0.15 deg. Run it with
  `python3 -m veleta_core --config config.wired.env` — the default
  `config.env` carries the WiFi layout and rejects both 6-field paths.
  **`SERIAL_PORT` is now empty by default and the port is found**: one
  USB-serial candidate is used and reported `(auto-detected)`, several are
  listed as an error, and an explicitly set port is never second-guessed. The
  USB cable carries data as well as power, and a classic Bluetooth module
  is the same path over the air: Windows pairs it as a virtual COM port and
  `SerialSource` reads it unchanged.
- **BLE still works and is still validated on real hardware** (2026-08-24):
  ATmega328P + HM-10 + MPU-6500, 39.7 Hz delivered, 0.3% loss, poses
  agreeing with the cable to 0.3 deg. Run it with
  `python3 -m veleta_core --config config.ble.env`. It is no longer what v1
  leads with — the cable is — but nothing about it has been removed or
  deprecated, and `sources/ble.py` ships in every package.
- **No WiFi sensor has ever been connected.** The WT901WIFI is owned but
  unconnected; the AVR WiFi sketch compiles (`arduino:avr:nano`, 38% flash /
  35% RAM), the ESP32 one is compile-untested.
- **The wired Windows package has run end to end on Windows** (reported
  2026-09-02, the partner's machine): sketch, USB serial, core, UDP,
  extension, scene. The earlier attempt (2026-08-27) had only got as far
  as the bundled `python.exe` finding the core before dying in
  `import bleak` on a missing `typing_extensions`, now shipped. That path
  was not retried: this run was the wired build, so **the radio has still
  never been touched from Windows**, and `bleak`'s WinRT backend remains
  the least-proven half of the product. That is a large part of why v1
  leads with the cable: the cable package carries none of it. Both builds are unsigned on purpose — test builds, not
  customer ones. See `docs/packaging.md`.
- The recording in `samples/` is **synthetic**, from `fake_sensor.py`.
- **One fault from the 2026-09-02 session is parked, not closed:** an
  object that turned by itself for several seconds and then stopped,
  holding the new heading. It is yaw by construction — the only axis with
  no absolute reference. It did not reappear when the partner cloned the
  sketch onto a second Arduino with a second MPU-6500 against the same core
  and extension (2026-09-03), which points at the first sensor but proves
  nothing: no recording was ever taken. **Jonathan parked the fixes on
  2026-09-03 — do not write them until the fault is reported again.** Full
  diagnosis and the candidate causes are in `docs/fieldnotes.md`.

## Known uncertainties (resolve with hardware in hand)

1. **The WT901WIFI's real CSV layout.** `IDX_ANGLE_X/Y/Z=7,8,9` and
   `IDX_DEVICE=0` come from the product documentation and may vary with
   firmware. Confirm with `core/tools/read_udp.py`, adjust `config.env`.
2. **Axis frames.** Nothing is validated against a real mounting; the
   defaults are identity precisely because it is unknown. Note that the
   axis map is now applied **after** the calibration offset, where it used
   to be applied before — see "known differences" in `docs/context.md`.
   Do not copy old `AXIS_MAP` values expecting the same result.
   The 2026-09-02 session was the first real mounting the product has ever
   seen, so whether the partner had to touch `AXIS_MAP` / `SIGN_*` is worth
   asking before anyone changes anything — see `docs/fieldnotes.md`.
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
