# Protocol

Two contracts, and the difference between them matters.

| | Sensors → core | Core → consumers |
|---|---|---|
| Speaks | ASCII CSV, one line per reading | JSON, one object per datagram |
| Direction | One way | Commands out, poses back |
| Who implements it | The firmware | The Blender extension, tools, a future Godot adapter |
| Why it is documented | So a new sensor can join without touching the core | So a consumer is an independent program, not a plug-in of the core |

The second one is load bearing beyond engineering. The core is proprietary
and the Blender extension is GPL v3 or later, and what keeps that coherent
is that they are two programs communicating over a documented protocol —
not one program in two files. Anyone can write a consumer against this
document without any of the core's source, which is the practical test of
that claim.

---

## Part 1 — Sensors → core

Every sensor emits **ASCII CSV, one line per reading**, terminated by
`\r\n`. There is a single field layout, shared by all transports and all
hardware. A sensor may emit a **prefix** of it: the receiver decides what
it can do from the number of fields it gets.

```
index   0         1   2   3    4   5   6     7      8      9      10  11  12
field   deviceId  ax  ay  az   gx  gy  gz    angX   angY   angZ   mx  my  mz
unit    string    g   g   g    °/s °/s °/s   deg    deg    deg    (raw)
```

### Profiles

| Profile | Fields | Who emits it | What the core does |
|---|---|---|---|
| `raw6` | 7 (`0..6`) | `mpu_wifi_avr_esp01`, `mpu_wifi_esp32` | Fuses it (complementary filter), per device |
| `fused` | 13 (`0..12`) | WitMotion WT901WIFI | Uses `angX/Y/Z` directly (fused by the sensor's Kalman) |

`raw6` is deliberately a **prefix** of the WitMotion layout: the same
`IDX_*` config keys address both, and adding a profile later (a native
quaternion appended at 13..16, say) does not break existing sensors.

### Point-to-point transports are the exception

The wired path and the BLE path both stream **6 fields with no deviceId**
(`ax,ay,az,gx,gy,gz`). That is fine and stays as it is: a cable carries
exactly one sensor, and so does one BLE connection, so there is nothing to
disambiguate. Do not add a deviceId there — the transport already
identifies the device.

The core names the sensor from `SERIAL_DEVICE_ID` on the wire, and on BLE
from the **peripheral's advertised name** (set with `AT+NAME`), which
makes the identity a property of the module rather than of the PC's
config. On a link that carries ~1990 B/s, spending ~7 bytes per frame on a
constant string would cost real frames per second.

### deviceId

- Free-form string, no commas, no spaces. It is the **identity of a board**,
  not of a model: it is what the extension maps to a Blender object or
  (later) an armature bone.
- WT901WIFI: assigned by its firmware, looks like `WT53xxxx`. Discover it
  with `core/tools/read_udp.py` or the `devices` command.
- Arduino/ESP boards: **you** choose it, in each board's `secrets.h`
  (`DEVICE_ID`). Give each board of a suit a distinct one, e.g. `ARM_L`,
  `ARM_R`, `SPINE`.

### Transport

- **UDP**, one datagram per frame, no ACK, no reconnection logic. A lost
  frame is a lost frame: the next one carries a fresher pose, which is what
  you want for motion capture. Never TCP — a retransmit delivers a stale
  pose late, which is worse than not delivering it.
- A datagram **may** contain more than one line (some firmwares batch). The
  core processes the **last complete line** of each datagram.
- Default port `1399` (`LISTEN_PORT` in `core/config.env`). It must match
  what is configured on every sensor.

### Rate

| Source | Realistic rate | Why |
|---|---|---|
| `mpu_wifi_avr_esp01` | ~20 Hz | SoftwareSerial + AT commands is the bottleneck |
| `mpu_wifi_esp32` | 100–200 Hz | Native WiFi, no intermediary |
| WT901WIFI | up to 200 Hz | Configured from WitMotion's tool |
| wired (serial) | **39 Hz (measured)** | `delay(20)` plus ~5.5 ms of I2C read and printing |
| BLE (HM-10 @38400) | **40 Hz (measured)** | ~1990 B/s link; rate is `1990 / frame_bytes` |

The core drains up to 200 datagrams per loop, so several sensors at 100 Hz
are fine.

The wired and BLE figures are measured, not estimated. Wired: 25.5 ms
median period (p5 24.7, p95 26.3) over 20 s on the bench Nano. BLE, paced
at 40 Hz: 39.7 Hz delivered, 0.3% loss, 1194/1196 frames well formed. The `delay(20)` is only part of it —
the I2C burst and the `Serial.print` of the line cost the rest. The others
remain estimates until the same measurement is made on them.

### Adding a new sensor type

1. Make it emit this layout (a prefix is fine); pick a `deviceId`.
2. Point it at `CORE_IP:1399`.
3. Verify with `python3 core/tools/read_udp.py 1399 10` — check the field
   count and that the values sit where this document says.
4. If the layout differs and you cannot change the firmware, adjust the
   `IDX_*` in `core/config.env`. **Never** patch the parser for a
   field-order difference; that is what the indices are for.

---

## Part 2 — Core → consumers

One UDP socket, default port `1400` (`CONTROL_PORT`), bound to `127.0.0.1`
by default: the core is not on the network unless you put it there. Every
message in both directions is **one JSON object per datagram**.

### Why subscription, and not a configured destination

A consumer sends `{"cmd": "subscribe"}` and the core streams poses back to
the address that datagram came from, for `SUBSCRIPTION_TTL` seconds,
renewed by subscribing again.

So: the core needs no consumer IP configured, two consumers can watch at
once (Blender and a diagnostic tool), a consumer that crashes stops being
sent to on its own, and the version handshake and the commands ride the
same socket the poses come back on. A consumer that can receive poses can
always ask what version it is talking to.

### Commands

| Command | Payload | Reply |
|---|---|---|
| `hello` | — | version, protocol, devices |
| `subscribe` | `ttl` (seconds, optional) | as `hello`, plus `subscribed: true` |
| `unsubscribe` | — | `{"ok": true, "subscribed": false}` |
| `calibrate` | — | `{"ok": true, "calibrated": <n>}` |
| `recenter` | `device` | `{"ok": <bool>, "device": …}` |
| `devices` | — | `{"ok": true, "devices": [...]}` |

Every reply carries `ok`. An unknown command, a malformed datagram or a
non-JSON payload is answered with `{"ok": false, "error": …}` — never
ignored, and never fatal to the core.

```json
{"ok": true, "type": "hello", "version": "0.1.0", "protocol": 1,
 "devices": [{"id": "WT53abc", "profile": "fused", "calibrated": true,
              "frames": 1042, "ready": true}]}
```

### The version handshake

`hello` carries the core's `version`. Firmware, core and extension share
one version number and ship together, so a mismatch means the user updated
one piece and not the others. **A consumer must compare and say so
visibly.** This is not ceremony: old firmware against new software is the
commonest fault in a product like this, and from the symptoms alone it is
miserable to diagnose.

`protocol` is separate and moves far more slowly: it is bumped only when a
change would break an existing consumer.

### Pose frames

Streamed to every live subscriber, one datagram each:

```json
{"type": "pose", "t": 1755012345.678, "dev": "WT53abc", "profile": "fused",
 "q": [0.9619, -0.2195, -0.1013, -0.1170], "rpy": [3.5, -18.39, -12.57]}
```

- `q` — the orientation, **calibrated** (the reference pose already
  removed), as a unit quaternion `(w, x, y, z)`, **in the sensor's own
  frame**.
- `rpy` — the **uncalibrated** fused angles in degrees. Diagnostic: it is
  what the sensor reads, which is how a user sees drift for what it is.
- `t` — the core's timestamp for the reading.

### Why orientation is not mapped to any engine's axes

`q` is in the sensor's frame, and turning it into scene axes is the
consumer's job. Blender is Z-up, Godot is Y-up, and how a sensor is
physically strapped to a thing is a property of the mounting, not of the
core. So the `AXIS_MAP` and `SIGN_*` knobs live in the consumer — in the
extension's preferences — and the core stays engine-agnostic, which is what
makes the Godot adapter a matter of writing a consumer rather than
extending the core.

---

## Part 3 — Recordings (`samples/*.jsonl`)

One JSON object per line, holding the **sensor** stream — Part 1, not
Part 2:

```json
{"t": 0.0,      "line": "WT53abc,-0.2895,0.0000,0.9572,24.0000,…"}
{"t": 0.024507, "line": "WT53abc,-0.2953,0.0100,0.9554,23.9952,…"}
```

- `t` is seconds **relative to the first frame**, so a recording is
  comparable between machines and replays at its original rate.
- Lines starting with `#` are comments. Unparseable lines are skipped
  rather than fatal: a recording truncated by a crash is exactly the
  recording you most want to replay.

It holds the sensor stream and not the core's output on purpose. Replaying
it exercises parsing, fusion and calibration the way live hardware would,
which is what makes one file serve three jobs: the fixture the tests run
against, the way to reproduce a fault from a recording a user sent without
their hardware on your desk, and a working setup when the sensor is flat,
broken or in another room.

Note that this is the **core's** playback, so it is for people who have a
core — which means people who have a kit. Somebody who installed only the
extension has no core at all; the extension carries its own small recording
and replays it by itself, which is a different mechanism for a different
audience. See `blender/playback.py`.

```bash
python3 -m veleta_core --record ../samples/new.jsonl     # capture
python3 -m veleta_core --play ../samples/new.jsonl --loop # replay
```


### BLE: never out-run the link

The BLE link is a fixed pipe of about **1990 B/s** (HM-10 at 38400), so
the frame rate is simply `1990 / frame_bytes` — 45 Hz for a 45-byte raw6
frame, and no configuration will beat that.

Exceeding it is not a graceful degradation. The HM-10 **drops bytes
mid-line**, not whole frames, and the debris still satisfies this
document: a truncated `-0.3044` arrives as `44`, the line still carries
six numeric fields, and the core parses 44 g as a real acceleration.
Free-running at 66 Hz delivered 45.2 Hz but only **388 of 1364 frames well
formed**.

The emitter must therefore be paced below the ceiling — that is what
`TX_PERIOD_MS` in `mpu_ble_hm10.ino` is, and why it is documented as a
safety limit rather than a tuning knob. The consumer's defence is smaller:
the core discards everything before the first newline after connecting,
because that fragment is a truncated frame by definition.
