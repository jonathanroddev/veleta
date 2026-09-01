# Changelog

Firmware, core and extension share one version number and are released
together. A release is only complete when all three carry it: the
extension asks the core for its version on connecting and says so, in the
panel, when they disagree.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- `core/` — a standalone process that reads the sensors, fuses their
  readings, calibrates them and re-exposes orientation over UDP. It does
  not import `bpy` and runs with no Blender on the machine.
- Core to consumer protocol: JSON over UDP, subscription based, with a
  version handshake and calibration commands. See `docs/protocol.md`.
- File playback (`--play`) and recording (`--record`) of the sensor stream,
  so the product can be demonstrated, tested and debugged with no hardware.
- `blender/` — the extension, now a consumer of the core rather than a
  loose script: preferences, a sidebar panel, connect, calibrate and
  per-sensor recenter.
- A built-in demo in the extension: **Play demo** replays a bundled
  recording with no core, no sensors and no network, so the extension is
  useful to somebody who installed it without buying a kit.
- `tests/` — 76 tests covering the quaternion math, frame parsing, the
  complementary filter, calibration, the protocol over real sockets, the
  shipped recordings and the bundled demo.
- `scripts/build_extension.py` — reproducible extension package.
- **BLE transport** (`--source ble`). `firmware/ble/` holds the sensor
  sketch and a bring-up tool that finds the module's pins and sets its
  baud and name; `core/veleta_core/sources/ble.py` is the client,
  with `bleak` imported lazily like `pyserial`. Validated on hardware:
  39.7 Hz delivered, 0.3% loss, poses agreeing with the cable to 0.3 deg.
- `core/config.ble.env` and `docs/setup_ble_hm10.md`.
- The BLE device id is the peripheral's advertised name (`AT+NAME`), so
  identity is a property of the module and costs nothing on the wire.
- **A wired-only Windows core package**, built by
  `scripts/build_windows_bundle.py --wired-only` and shipped as
  `veleta-core-wired-<version>-win64.zip`. It carries the cable path and
  nothing else: no WiFi or BLE configuration, no launcher for either, and
  none of the eleven bleak/WinRT wheels. Smaller, and it cannot fail in the
  half of the product that has never run on Windows.
- `packaging/windows/veleta-core-wired.bat`, in both Windows packages: the
  cable path had no launcher of its own and had to be reached by passing
  `--config config.wired.env` to a `.bat` named after the WiFi one.
- `packaging/windows/README-wired.txt`, packed inside the wired package
  under the name `README.txt`, so that buyer reads a document with no
  branches for hardware that is not in the box.
- **A Spanish installation guide as a PDF**, `Guia-de-instalacion.pdf`,
  inside the wired package. Four A4 pages covering only the cable path:
  what is on the drive, unzipping the core, finding the COM port with
  `list-ports.bat`, installing the extension, the first run in order, and a
  symptom table for when nothing moves. Rendered from
  `packaging/windows/guia-instalacion-es.html`; both are committed and the
  build packs the PDF verbatim, so the package stays byte-reproducible and
  the build needs no PDF toolchain. `--check` refuses to build when the PDF
  is older than the HTML.

### Fixed
- The bundled demo no longer depends on a coincidence. `veleta-core-demo.bat`
  passed no `--config`, so it read whatever the package happened to carry —
  and the wired package carries no `config.env`, leaving it on the built-in
  defaults, which match the recording's layout by luck rather than by
  intent. It now passes `core/config.demo.env`, which ships in both
  packages, and `tests/test_playback.py` replays every sample through that
  file instead of through `DEFAULTS`.
- The bench sensor is an **MPU-6500**, not an MPU-6050: `WHO_AM_I` (0x75)
  reads 0x70. The sketch header claimed "confirmed by WHO_AM_I=0x68", which
  confused the I2C address with the WHO_AM_I value. No code change was
  needed — the two parts are register-compatible for everything the sketch
  touches.
- The wired rate is **39 Hz measured**, not the ~50 Hz `docs/protocol.md`
  claimed: the `delay(20)` is only part of a 25.5 ms period.
- The Windows bundle now ships `typing_extensions`, without which the BLE
  path died on `import bleak` before touching the radio. `winrt-runtime`
  requires it on every Python version; bleak's own metadata asks for it
  only below 3.12, so on the 3.13 interpreter the bundle embeds it looked
  unnecessary and was not.
- `config.ble.env` listed no `BLE_*` key at all — the one file whose whole
  reason to exist is the BLE path had nothing to point at a module — and
  labelled its serial block `(SOURCE=ble)`. The empty defaults did work
  (first peripheral advertising the HM-10 service), so the gap only shows
  with a second module in range, or when a scan finds nothing and there is
  no documented knob to turn.
- `core/config.wired.env` — the wired bench could not be run from the
  shipped configuration. `config.env` carries the WiFi layout (7 fields
  with a DeviceID) while the wired path sends 6 fields without one, so
  every frame was rejected as UNPARSED. This is a second configuration,
  not a second parser.

### Changed
- **The cable is the product path.** The plan of 2026-08-24 was that the
  final assembly ran on a battery and USB was power only, which made BLE
  the path and the cable a bench. v1 leads with the cable instead: it is
  the path that is proven end to end, and `bleak`'s WinRT backend is still
  the least-exercised code in the product. **Nothing about BLE was removed
  or deprecated** — the firmware, `sources/ble.py` and `config.ble.env` all
  ship, and `sources/ble.py` travels even in the wired-only package.
- Split out of `sandbox/motion_bridge`, where the fusion lived inside the
  Blender scripts. The transports are now sources of one core rather than
  separate programs.
- `pyserial` is no longer needed inside Blender. It is an optional
  dependency of the core, used only by the wired bench.
- The diagnostic readers (`read_udp.py`, `read_serial.py`) now interpret
  each frame with the core's own `Layout` and print a summary, so they
  answer "do my `IDX_*` match this sensor?" directly instead of leaving you
  counting commas.
- The axis mapping (`AXIS_MAP`, `SIGN_*`) moved to the consumer side and is
  therefore applied AFTER the calibration offset, where it used to be
  applied before. See "known differences" in `docs/context.md`.

[Unreleased]: https://github.com/jonathanroddev/veleta
