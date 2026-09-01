# Setting up the BLE sensor (HM-10)

The battery path: an ATmega328P board + MPU-6500/6050 + an HM-10 module,
streaming to the core over Bluetooth Low Energy. No cable for data, no
mains for a WiFi radio.

> **v1 ships the cable, not this** (decided 2026-08-31). Everything in this
> guide still works and is still supported — the path is validated on
> hardware and `sources/ble.py` ships in every package. It is not what the
> product leads with, because `bleak`'s WinRT backend has never run on
> Windows. See [`hardware.md`](hardware.md#the-ble-path-the-battery-assembly).

Firmware: [`firmware/ble/mpu_ble_hm10/`](../firmware/ble/mpu_ble_hm10/).
Bring-up tool: [`firmware/ble/hm10_config/`](../firmware/ble/hm10_config/).

## Read this first: BLE is not Bluetooth Classic

They share a name and nothing else that matters here.

| | Bluetooth Classic (HC-05/06) | BLE (HM-10) |
|---|---|---|
| Pair it in the OS? | Yes | **No** |
| Becomes a COM / `/dev/cu.*`? | Yes | **Never** |
| Core support | `--source serial` | `--source ble` |

An HM-10 **will not appear in the system Bluetooth pane** and you cannot
pair it. That is not a fault. A BLE peripheral exposing a vendor service
is invisible to the pairing UI and reachable only from a program that
speaks GATT — which is what `--source ble` is.

Tell them apart by the reply: an HM-10 answers `OK+Get:...`, takes
commands with **no CR/LF terminator**, and exposes service `0xFFE0` with
characteristic `0xFFE1`. An HC-05 answers `+NAME:...` then `OK` and wants
a terminator.

## Wiring

| MPU-6500 | Board |
|---|---|
| VCC | 5V |
| GND | GND |
| SCL | A5 |
| SDA | A4 |

| HM-10 | Board |
|---|---|
| TX | D2 |
| RX | D3 |
| VCC / GND | 5V / GND |

D2/D3 is the same pair `mpu_wifi_avr_esp01` uses for its radio. If yours
is wired elsewhere, do not guess — flash `hm10_config/`, which sweeps
every pin pair and tells you.

## 1. Find and configure the module

Flash `firmware/ble/hm10_config/`, open the serial monitor at 115200 and
set it to **"No line ending"**. It reports the pins and the current baud,
then becomes a transparent AT bridge.

Two settings matter:

```
AT+BAUD2            38400. Do not skip this one.
AT+NAME<name>       the device id the core will use. No commas, no spaces.
```

Check with `AT+BAUD?` (expect `OK+Get:2`) and `AT+NAME?`.

**Why 38400 is not optional.** At the factory 9600 the link carries
~944 B/s and the *UART*, not the radio, is the bottleneck: ~21 frames/s.
At 38400 it carries ~1990 B/s and the ceiling doubles to ~45. Measured,
both of them.

`AT+BAUD2` is persistent and survives power cycles. Revert with `AT+BAUD0`.
It breaks any other sketch still bridging at 9600.

> AT commands only work while **nothing is connected** to the module over
> BLE. If it has gone quiet, close whatever is talking to it.

## 2. Flash the sensor sketch

```bash
arduino-cli compile --upload -b arduino:avr:nano:cpu=atmega328old \
  -p /dev/cu.usbserial-XXXXXXXX firmware/ble/mpu_ble_hm10
```

`cpu=atmega328old` because the bench Nano is an original board whose
bootloader syncs at 57600. On a clone, drop it.

> Uploading over a sketch that transmits continuously can lose the
> bootloader's ~1 s window. If `avrdude` will not sync, just retry — it
> usually wins within a couple of attempts.

## 3. Run the core

```bash
python3 -m pip install bleak
cd core
python3 -m veleta_core --config config.ble.env
```

`config.ble.env`, not `config.env`: BLE frames are 6 fields with no
DeviceID, so every `IDX_*` shifts down by one. Point the default config at
a BLE module and every frame is rejected as `UNPARSED`.

With one module the core connects to the first peripheral advertising
`0xFFE0`. With several, set `BLE_NAME` — that is what `AT+NAME` was for.

On macOS the first run raises a Bluetooth permission prompt. A terminal
that was denied reports *"Bluetooth device is turned off"* even with the
adapter on; grant it in **System Settings > Privacy & Security >
Bluetooth**.

## The rule: never out-run the link

`TX_PERIOD_MS` in the sketch is 25 ms (40 Hz), under the measured ~45 Hz
ceiling. It is a safety limit, not a performance knob.

Over-running does **not** cost you whole frames. The HM-10 drops **bytes
mid-line**, and the debris still parses: a cut `-0.3044` arrives as `44`,
the line still has six numeric fields, and the filter swallows 44 g as a
real reading. Measured free-running at 66 Hz: 45.2 Hz delivered, but only
**388 of 1364 frames well formed**. Paced at 40 Hz: 39.7 Hz delivered,
0.3% loss, **1194 of 1196 well formed**.

If you shorten the frame you may raise the rate — the link is a fixed
~1990 B/s pipe, so rate is `1990 / frame_bytes`. Re-measure before
trusting it.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Not in the system Bluetooth pane | Normal. BLE never appears there. |
| `no BLE peripheral advertising...` | Something is already connected to it; a module in use stops advertising. |
| "Bluetooth device is turned off", adapter on | macOS permission, see above. |
| AT commands silent | Something is connected over BLE, or you sent a terminator, or you waited <260 ms for the reply. |
| Every frame `UNPARSED` | Using `config.env` instead of `config.ble.env`. |
| ~21 Hz instead of ~40 | Module still at 9600. `AT+BAUD?` should say 2. |
| Wild values, |a| in the tens of g | Out-running the link. Check `TX_PERIOD_MS`. |
