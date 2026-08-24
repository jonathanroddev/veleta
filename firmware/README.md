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
├── ble/
│   ├── mpu_ble_hm10/           ATmega328P + HM-10 + MPU-6500, 40 Hz
│   └── hm10_config/            find the module's pins and set its baud/name
├── wifi/
│   ├── mpu_wifi_esp32/         ESP32 + MPU-6050, native WiFi, 100-200 Hz
│   └── mpu_wifi_avr_esp01/     ATmega328P + ESP-01 + MPU-6050, ~20 Hz
└── wired/
    ├── mpu_serial_bridge/      Nano + MPU-6500 over USB serial, 39 Hz
    ├── i2c_diag/               I2C scan: is the sensor even there?
    └── backups/                flash/EEPROM dumps (gitignored)
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

## The BLE path is the product path

`ble/` is where the kit is going: the final assembly runs on a battery, so
there is no cable to carry data and no mains to feed a WiFi radio. It
measures **39.7 Hz delivered with 0.3% loss**, which beats the wired bench
and matches what the ESP32 would give on a fraction of the power.

It has one hard rule, spelled out in the sketch: **never out-run the
link**. Over-running does not drop whole frames — the HM-10 drops bytes
mid-line, and the debris still parses as six numeric fields.

## State

`ble/mpu_ble_hm10` and `wired/` are **flashed and validated on real
hardware**. The WiFi sketches are written and **never flashed**. See
[`docs/hardware.md`](../docs/hardware.md) for exactly what has and has not
been done, and the setup guides for bring-up.

## Version

Firmware, core and extension share one version number and ship together.
When you flash a board, flash the version the rest of the kit is on: the
extension warns the user when the core disagrees with it, and the same
discipline applies here.
