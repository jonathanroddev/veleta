# firmware — what runs on the board

Sketches for the microcontrollers. They read the IMU and emit the CSV
stream defined in [`docs/protocol.md`](../docs/protocol.md). They do not
fuse, filter or calibrate: that happens in the [core](../core/), so the
filter can be iterated without reflashing anything — and, with a suit,
without reflashing *N* boards.

## Licence

**Proprietary, all rights reserved.** See [`LICENSE`](LICENSE). This is not
PC software: it is burned onto a microcontroller, and it is not
distributed with the Blender extension.

## Layout

```
firmware/
├── wired/                      the v1 path
│   ├── mpu_serial_bridge/      Nano + MPU-6500 over USB serial, 39 Hz
│   ├── i2c_diag/               I2C scan: is the sensor even there?
│   └── backups/                flash/EEPROM dumps (gitignored)
├── ble/
│   ├── mpu_ble_hm10/           ATmega328P + HM-10 + MPU-6500, 40 Hz
│   └── hm10_config/            find the module's pins and set its baud/name
└── wifi/
    ├── mpu_wifi_esp32/         ESP32 + MPU-6050, native WiFi, 100-200 Hz
    └── mpu_wifi_avr_esp01/     ATmega328P + ESP-01 + MPU-6050, ~20 Hz
```

`mpu_wifi_avr_esp01/` is named after the **architecture, not the board**.
It is board-agnostic 328P code: Nano by default, Uno with a different FQBN.
Do not fork it per board — the difference is a build flag, not code.

## Credentials

Network credentials live in `secrets.h`, one per board, **gitignored**.
Copy `secrets.example.h` to start. Never commit an SSID, a password or a
LAN IP.

BLE needs none: there is no network to join. The module's identity is its
advertised BLE name, set with `AT+NAME`, and the core uses it as the
device id — so a BLE board has nothing secret to keep out of the repo.

## Which path the kit ships

**`wired/` is the product path for v1** (decided 2026-08-31). The USB lead
carries the readings as well as the power, `mpu_serial_bridge` measures
**39 Hz**, and it is the path with nothing unproven under it on the PC side:
the core reads it with `pyserial`, which is pure Python and ships in every
package.

**`ble/` is fully supported and is not going anywhere.** It measures
**39.7 Hz delivered with 0.3% loss** — slightly better than the cable — and
it is what a battery assembly needs, since a board on a battery has no lead
to carry data and no mains to feed a WiFi radio. What moved it out of first
place is not the radio but the PC end: `bleak`'s WinRT backend has still
never been exercised on Windows, so the cable is the path that can be
shipped with nothing unknown in it.

`ble/` has one hard rule, spelled out in the sketch: **never out-run the
link**. Over-running does not drop whole frames — the HM-10 drops bytes
mid-line, and the debris still parses as six numeric fields.

## State

`wired/` and `ble/mpu_ble_hm10` are **flashed and validated on real
hardware**. The WiFi sketches are written and **never flashed**. See
[`docs/hardware.md`](../docs/hardware.md) for exactly what has and has not
been done, and the setup guides for bring-up.

## Version

Firmware, core and extension share one version number and ship together.
When you flash a board, flash the version the rest of the kit is on: the
extension warns the user when the core disagrees with it, and the same
discipline applies here.
