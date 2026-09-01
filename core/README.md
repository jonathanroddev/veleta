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
python3 -m veleta_core --config config.wired.env   # a sensor on USB (the v1 path)
python3 -m veleta_core --config config.ble.env     # an HM-10 module
python3 -m veleta_core                             # WiFi sensors on UDP 1399
python3 -m veleta_core --play ../samples/wt901_desk_wobble.jsonl --loop
python3 -m veleta_core --record ../samples/new.jsonl
python3 -m veleta_core --config config.wired.env --serial-port /dev/cu.usbserial-110
python3 -m veleta_core --help
```

**Each transport has its own configuration file, and it is not optional.**
The wired and BLE boards send six fields with no device id; `config.env`
describes the WiFi layout. Point the core at the wrong one and every frame
is reported UNPARSED — which is the intended outcome, not a bug: a layout
is configuration, so a mismatched layout has to fail loudly rather than
half-parse.

Consumers connect on UDP **1400** and subscribe; the core streams poses
back to whoever asked, and answers `calibrate`, `recenter`, `devices` and
`hello` on the same socket.

## Configuration

KEY=value, read with no external dependency. Ports, field indices, filter
constants. Three files ship, one per sensor layout:

| File | For | Fields |
|---|---|---|
| [`config.wired.env`](config.wired.env) | USB cable, or a classic Bluetooth module on a virtual COM port | 6, no device id |
| [`config.ble.env`](config.ble.env) | an HM-10 BLE module | 6, no device id |
| [`config.env`](config.env) | WiFi sensors over UDP — **the default** | 7+, with a DeviceID |
| [`config.demo.env`](config.demo.env) | the recordings in `samples/`, replayed with `--play` | 13, with a DeviceID |

Pass one with `--config`. Without it the lookup order is
`$VELETA_CORE_CONFIG`, `config.env` in the working directory, then the
`config.env` shipped here; with none of those present the built-in defaults
apply, and those are the WiFi layout.

Two rules that have not changed and should not:

- **A different CSV layout is a configuration change**, never a parser
  change. That is what the `IDX_*` keys are for.
- **Axis mapping is not here.** It belongs to the consumer, because Blender
  is Z-up and Godot is Y-up. See [`docs/context.md`](../docs/context.md).

## Dependencies

The standard library, and that is the whole list for the WiFi path. Two
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
├── config.env          WiFi layout, and the default
├── config.wired.env    USB cable / classic Bluetooth
├── config.ble.env      HM-10
├── config.demo.env     the bundled recordings
├── veleta_core/
│   ├── __main__.py      the loop: drain, fuse, broadcast, answer
│   ├── engine.py        devices, calibration, orchestration
│   ├── frames.py        sensor CSV -> Reading. Never patch it for a layout
│   ├── fusion.py        complementary filter, per device
│   ├── quat.py          quaternion math (no mathutils outside Blender)
│   ├── server.py        the core <-> consumers socket
│   ├── recorder.py      writing .jsonl recordings
│   └── sources/         udp · serial · ble · file
└── tools/
    ├── read_udp.py      what is arriving, and in what format
    ├── read_serial.py   the same, for the wired bench
    └── fake_sensor.py   a physically consistent sensor, with no hardware
```
