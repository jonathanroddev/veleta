# Installation

> Written for the person who bought a kit. It is the destination of the QR
> code on the card in the box, and the source the Spanish versions are
> written from: the download site's guide, and
> `packaging/windows/guia-instalacion-es.html`, which is rendered to the
> PDF that ships inside the wired package. **Change here first**, then
> carry the change across — nothing enforces that they agree.

There are two pieces to install, in this order.

## 1. The core

The core is the program that talks to the sensors. It comes with the kit.

**Windows.** Unzip the core package anywhere you like. It installs nothing
and changes nothing on your machine: the copy of Python it needs travels
inside the folder. Then start the file that matches your sensor.

The **cable kit** carries `veleta-programa-<version>-windows-x64.zip`, which
holds that path and nothing else — one launcher to start, one file to
configure:

| Your sensor | Start |
|---|---|
| USB cable (the standard kit) | `veleta-sensor.bat` |
| None yet | `diagnostico\veleta-demo.bat` |

Other kits will carry their own package, built the same way and holding
only their path. There is deliberately no package with every sensor mode in
it: you bought one kit, and a folder full of launchers for hardware you do
not own is a folder with a wrong file to double-click in it.

Whichever you start, it reports what it is listening on and waits. Leave it
running: Blender talks to it while you work.

The core does not need an internet connection and does not send anything
anywhere: by default it listens on your own machine only.

**macOS** may say the app cannot be opened because it is from an
unidentified developer, and **Windows** may show a SmartScreen warning.
See [`packaging.md`](packaging.md#signing) for where that stands.

## 2. The extension

The kit carries it as a zip, `veleta-extension-blender-<version>.zip`. Note it is the small
one, around 30 KB — not the core package, which is far bigger.

1. **Edit → Preferences → Add-ons → ▾ → Install from Disk…**
2. Pick `veleta-extension-blender-<version>.zip` from the kit.
3. Tick it to enable it, if it is not already.

The same **Install from Disk…** sits under **Get Extensions → ▾**; either
menu does the same thing. Dragging the zip onto the Blender window works
too.

**Blender 4.2 or newer is required.**

## 3. What to configure

Very little: one line in a text file on the cable kit, and one setting in
Blender that a default scene already satisfies.

### The core: one line on the cable kit

The configuration file beside it already matches the sensor in the box,
with one exception that is not optional.

**On the cable kit, plug the sensor in and start the launcher.** Windows
assigns the port number itself, so it cannot be shipped right — but it does
not have to be typed either: with the sensor as the only USB-serial device
connected, the core finds it and says `(auto-detected)` beside the port it
chose.

With several such devices connected it will not guess. It lists them and
stops, and you settle it:

1. Note the port from the list it printed — or run
   `diagnostico\ver-puertos.bat` to see the same list on its own.
2. Open `ajustes-sensor.txt` (a double-click opens it in Notepad) and set
   `SERIAL_PORT` to it, e.g. `SERIAL_PORT=COM5`. Save.

That holds until you plug the sensor into a different socket. If you would
rather not edit anything, pass it instead:
`veleta-sensor.bat --serial-port COM5`.

> None of the port failures are silent: "none could be found" when nothing
> is connected, "more than one to choose from" when the choice is yours,
> "could not open port..." when the one named went away. They are the
> failures in this guide that say exactly what is wrong.

On the Bluetooth kit the setting worth knowing exists is `BLE_NAME` in
`ajustes-bluetooth.txt`. Shipped empty, which means "connect to the first
veleta sensor you find" — right for one sensor, ambiguous for several. When
you own more than one, put the name of the one you want there.

### The extension: one setting

Its defaults already point at the core: **Core host** `127.0.0.1` and
**Core port** `1400` are exactly where the core listens.

That leaves one that matters:

**Sensor → object** — which object each sensor drives. It ships as
`*:Cube`, where `*` means "any sensor" and `Cube` is the cube a brand new
Blender scene starts with. On a default scene it therefore works untouched.
Change `Cube` to your object's exact name from the outliner if you deleted
that cube or want to drive something else.

> If the name matches no object, the sensor falls through to **Default
> object** (`_UNASSIGNED`), which does not exist either. Then nothing moves
> and nothing complains. It is the most common first-run disappointment and
> it is not a fault — check the name against the outliner, spelling and
> capitals included.

**Axis map** and the three **Sign** values start at identity on purpose:
the right values depend on how you physically mounted the sensor, so there
is no default that could be right. Expect to set them once, after mounting
it — see [When the object moves wrongly](#when-the-object-moves-wrongly).

## 4. First run

1. Connect the sensor.
   - *Cable kit:* the USB lead carries the readings as well as the power,
     so plug it into the machine running the core rather than into a phone
     charger. Set `SERIAL_PORT` once — see [What to
     configure](#3-what-to-configure).
   - *Bluetooth kit:* the USB lead is **power only** — there is no driver
     to install and nothing to pair. A veleta sensor never appears in your
     system's Bluetooth settings, and that is normal: it is not that kind
     of Bluetooth device. The core finds it on its own. Windows and macOS
     both ask permission to use Bluetooth the first time.
2. Put the sensor **flat and still** on the desk. The core spends its first
   couple of seconds estimating the gyro's resting bias, and a sensor that
   moves during it will drift afterwards. You have about three seconds from
   the moment it starts.
3. In Blender, open the **Veleta** tab in the 3D viewport sidebar
   (press `N` if the sidebar is hidden).
4. Press **Connect**. The panel reports the core's version and the sensors
   it can see.
5. Check **Sensor → object** in the extension's preferences names an
   object that exists — see [What to configure](#3-what-to-configure). On a
   default scene the shipped `*:Cube` already does.
6. Hold the sensor in the pose you want to count as zero and press
   **Calibrate**.
7. Move the sensor. The object follows.

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
2. **Did you start the right one?** A cable sensor needs
   `veleta-sensor.bat` and a Bluetooth one `veleta-sensor-bluetooth.bat`.
   `veleta-sensor-wifi.bat` listens for WiFi sensors and will wait for them
   all day without saying so.
3. **Is the sensor powered, and is the core finding it?**
   - *Cable:* this one does not fail quietly. "none could be found" means
     nothing is plugged in. "could not open port..." means the lead came
     out, or another program is holding it — including a second copy of the
     core, so close any other window you left running. "more than one to
     choose from" means several devices are connected and the core will not
     pick for you; `diagnostico\ver-puertos.bat` shows the same list again. If frames
     arrive but every one is reported UNPARSED, the core is reading a real
     port with the wrong configuration: check you started
     `veleta-sensor.bat` and not another launcher.
   - *Bluetooth:* the core says which sensor it connected to as it starts.
     "no BLE peripheral advertising..." means it is unpowered, out of
     range, or something else is already connected to it — only one program
     can hold a sensor at a time, so close any other copy of the core.
     If your system insists Bluetooth is off while the adapter is plainly
     on, it is the permission that was refused, not the adapter: allow
     Bluetooth for the core in your system's privacy settings.
   - *WiFi:* its destination address has to be this machine and its port
     has to match the core's `LISTEN_PORT` (1399 by default).
4. **Does the panel list the sensor but nothing moves?** Then the sensor is
   arriving and the object name is wrong — check **Sensor → object** against
   the exact name in the outliner.
5. **Does the panel warn about versions?** Firmware, core and extension
   ship together. Update whichever is behind; a mismatch is not cosmetic.

## Seeing it work without the sensor

Useful when the sensor is flat, still in the box, or you are trying to work
out whether a fault is the sensor's. The two ways below are not the same
thing: they check different halves of the product, so which one you want
depends on what you are trying to find out.

**Press "Play demo" in the Veleta panel** — checks the *extension*. A short
recording ships inside the extension itself and replays against your scene,
with no core and no network involved. Set **Sensor → object** first, or the
movement has nowhere to go. If the object moves, then Blender, the
extension, your object mapping and your axis settings are all fine, and
anything still wrong is on the other side of the connection.

**Run the core with `--play`** — checks *everything except the sensor and
the radio*. The core replays the recording through its real parsing, fusion
and calibration, exactly as live hardware would:

```bash
veleta-core --play samples/wt901_desk_wobble.jsonl --loop
```

On Windows that is what `diagnostico\veleta-demo.bat` already does, so just
start it instead.

Connect from Blender as usual and the object moves. If it does, and a real
sensor does not, the fault is the sensor, its power or the network — not
the software.

> These come with your kit, so both are available to you. Somebody who
> installed only the extension has no core and therefore only the first
> one, which is exactly why it exists.
