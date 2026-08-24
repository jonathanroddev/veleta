# core — sensors in, oriented poses out

A plain program. It reads IMU sensors, fuses their readings, zeroes them
against a reference pose and re-exposes the result over UDP for anything
that speaks [the protocol](../docs/protocol.md).

**It does not import `bpy`,** and it runs, and is useful, with no Blender
on the machine. That independence is not incidental: it is what keeps this
component under its own licence while the Blender extension is GPL. See the
licence map in the [repository README](../README.md).

## Licence

**Proprietary, all rights reserved.** See [`LICENSE`](LICENSE). The source
being readable here is not a grant of licence.

## Running it

```bash
python3 -m veleta_core                          # WiFi sensors on UDP 1399
python3 -m veleta_core --play ../samples/wt901_desk_wobble.jsonl --loop
python3 -m veleta_core --record ../samples/new.jsonl
python3 -m veleta_core --source serial --serial-port /dev/cu.usbserial-110
python3 -m veleta_core --help
```

Consumers connect on UDP **1400** and subscribe; the core streams poses
back to whoever asked, and answers `calibrate`, `recenter`, `devices` and
`hello` on the same socket.

## Configuration

Everything lives in [`config.env`](config.env) — KEY=value, read with no
external dependency. Ports, field indices, filter constants. Looked up in
this order: `$VELETA_CORE_CONFIG`, `config.env` in the working directory,
then the one shipped here.

Two rules that have not changed and should not:

- **A different CSV layout is a configuration change**, never a parser
  change. That is what the `IDX_*` keys are for.
- **Axis mapping is not here.** It belongs to the consumer, because Blender
  is Z-up and Godot is Y-up. See [`docs/context.md`](../docs/context.md).

## Dependencies

The standard library, and that is the whole list for the WiFi kit. Two
transports need more, and both are imported lazily, so you only install
what you actually run:

```bash
python3 -m pip install pyserial     # only for --source serial
python3 -m pip install bleak        # only for --source ble
```

`bleak` is not the same kind of dependency as `pyserial`. `pyserial` is
pure Python; `bleak` is a facade over a compiled platform backend —
`pyobjc` on macOS, WinRT on Windows, D-Bus on Linux — so it is roughly
5-6 MB and it can fail to build on an old `pip`. It stays behind
`open_ble_source()` for that reason.

macOS also gates Bluetooth per application: the first run prompts, and a
terminal that was denied reports "Bluetooth device is turned off" even
though the adapter is on. Grant it in System Settings > Privacy &
Security > Bluetooth.

## Layout

```
core/
├── config.env
├── veleta_core/
│   ├── __main__.py      the loop: drain, fuse, broadcast, answer
│   ├── engine.py        devices, calibration, orchestration
│   ├── frames.py        sensor CSV -> Reading. Never patch it for a layout
│   ├── fusion.py        complementary filter, per device
│   ├── quat.py          quaternion math (no mathutils outside Blender)
│   ├── server.py        the core <-> consumers socket
│   ├── recorder.py      writing .jsonl recordings
│   └── sources/         udp · serial · file
└── tools/
    ├── read_udp.py      what is arriving, and in what format
    ├── read_serial.py   the same, for the wired bench
    └── fake_sensor.py   a physically consistent sensor, with no hardware
```
