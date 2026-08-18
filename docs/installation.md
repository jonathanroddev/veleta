# Installation

> Written for the person who bought a kit. It is the destination of the QR
> code on the card in the box. A Spanish translation lives on the download
> site; this file is the source it is written from.

There are two pieces to install, in this order.

## 1. The core

The core is the program that talks to the sensors. It comes with the kit,
as an installer for your operating system.

1. Open the installer and follow it.
2. Launch **vane core**. It reports the port it is listening on and waits.
3. Leave it running. Blender talks to it while you work.

The core does not need an internet connection and does not send anything
anywhere: by default it listens on your own machine only.

**macOS** may say the app cannot be opened because it is from an
unidentified developer, and **Windows** may show a SmartScreen warning.
See [`packaging.md`](packaging.md#signing) for where that stands.

## 2. The extension

From inside Blender, which is the easy path and keeps it updated:

1. **Edit → Preferences → Get Extensions**.
2. Search for **Vane**.
3. **Install**, then tick it to enable it.

Without an internet connection, the kit also carries the extension as a
zip:

1. **Edit → Preferences → Add-ons → ▾ → Install from Disk…**
2. Pick `vane-<version>.zip` from the kit.

Blender 4.2 or newer is required.

## 3. First run

1. Put the sensor **flat and still** on the desk. The core spends its first
   couple of seconds estimating the gyro's resting bias, and a sensor that
   moves during it will drift afterwards.
2. In Blender, open the **Vane** tab in the 3D viewport sidebar
   (press `N` if the sidebar is hidden).
3. Press **Connect**. The panel reports the core's version and the sensors
   it can see.
4. In the extension's preferences, put the name of the object you want to
   drive in **Sensor → object** (`*:Cube` means "any sensor moves the
   object called Cube").
5. Hold the sensor in the pose you want to count as zero and press
   **Calibrate**.
6. Move the sensor. The object follows.

## When the object moves wrongly

Almost always the mounting, not a fault. Two knobs in the extension's
preferences, and they fix different symptoms:

- **The object turns the right way but backwards** → flip the matching
  **Sign** (Roll, Pitch or Yaw).
- **You rotate one axis and a different one responds** → that is the
  **Axis map**. No combination of signs can fix it; move the source into
  the slot it should drive, e.g. `pitch,roll,yaw` swaps roll and pitch.

Rotate one axis at a time and watch which one answers.

## When nothing moves

In order, because the first two are almost always it:

1. **Is the core running?** The panel says "No core at 127.0.0.1:1400"
   when it is not.
2. **Is the sensor powered and on the same network?** For a WiFi sensor,
   its destination address has to be this machine and its port has to match
   the core's `LISTEN_PORT` (1399 by default).
3. **Does the panel list the sensor but nothing moves?** Then the sensor is
   arriving and the object name is wrong — check **Sensor → object** against
   the exact name in the outliner.
4. **Does the panel warn about versions?** Firmware, core and extension
   ship together. Update whichever is behind; a mismatch is not cosmetic.

## Seeing it work without the sensor

Useful when the sensor is flat, still in the box, or you are trying to work
out whether a fault is the sensor's. The two ways below are not the same
thing: they check different halves of the product, so which one you want
depends on what you are trying to find out.

**Press "Play demo" in the Vane panel** — checks the *extension*. A short
recording ships inside the extension itself and replays against your scene,
with no core and no network involved. Set **Sensor → object** first, or the
movement has nowhere to go. If the object moves, then Blender, the
extension, your object mapping and your axis settings are all fine, and
anything still wrong is on the other side of the connection.

**Run the core with `--play`** — checks *everything except the sensor and
the radio*. The core replays the recording through its real parsing, fusion
and calibration, exactly as live hardware would:

```bash
vane-core --play samples/wt901_desk_wobble.jsonl --loop
```

Connect from Blender as usual and the object moves. If it does, and a real
sensor does not, the fault is the sensor, its power or the network — not
the software.

> These come with your kit, so both are available to you. Somebody who
> installed only the extension has no core and therefore only the first
> one, which is exactly why it exists.
