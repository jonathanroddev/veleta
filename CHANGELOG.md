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
- `tests/` — 66 tests covering the quaternion math, frame parsing, the
  complementary filter, calibration, the protocol over real sockets, the
  shipped recordings and the bundled demo.
- `scripts/build_extension.py` — reproducible extension package.

### Changed
- Split out of `sandbox/motion_bridge`, where the fusion lived inside the
  Blender scripts. The wired and WiFi paths are now two sources of one
  core rather than two separate programs.
- `pyserial` is no longer needed inside Blender. It is an optional
  dependency of the core, used only by the wired bench.
- The diagnostic readers (`read_udp.py`, `read_serial.py`) now interpret
  each frame with the core's own `Layout` and print a summary, so they
  answer "do my `IDX_*` match this sensor?" directly instead of leaving you
  counting commas.
- The axis mapping (`AXIS_MAP`, `SIGN_*`) moved to the consumer side and is
  therefore applied AFTER the calibration offset, where it used to be
  applied before. See "known differences" in `docs/context.md`.

[Unreleased]: https://github.com/jonathanroddev/vane
