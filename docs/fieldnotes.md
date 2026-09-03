# Field notes

What actually happened on real machines, newest first. The rest of `docs/`
says how the product is meant to work; this file says what it did, and what
was left unresolved. An entry is written the day it is reported, with the
unknowns still marked as unknown — a field note that quietly resolves its
own open questions is worth nothing the next morning.

---

## 2026-09-03 — the fault did not follow the sketch to a second kit

Reported by the partner, not observed here. **No recording was taken**, so
nothing below is confirmed from raw data.

The partner cloned the working sketch onto a second Arduino with a second
MPU-6500, and ran it against the *same* core and the *same* Blender
extension. No fault appeared.

### What that narrows

The board, the sensor and the wiring all changed together, so which of the
three it was cannot be separated. What did *not* change is the software on
both sides of the UDP hop, which is the half that is now exonerated by
substitution.

The reading is that the first MPU-6500 — the first one the partner ever
assembled — was bad or badly wired. That is cause 1 of the 2026-09-02
entry (garbage frames the parser accepts, integrated permanently into
yaw), which was already the leading candidate. Causes 2, 3 and 4 are not
disproved: a fresh session re-estimates the gyro bias on every start,
thermal drift takes minutes to show, and the QuickEdit stall needs someone
to click the console. A short clean run does not distinguish *fixed* from
*latent*.

### What is still true regardless

- The core has no plausibility guard. `frames.py` accepts any line with six
  numeric fields, so the next bad sensor will fail exactly as silently as
  this one did.
- `mpu_serial_bridge.ino` still does not check `Wire.requestFrom`'s return.
- `engine.py:81` still has no upper clamp on `dt`.
- There are now **two** kits in circulation and still no way to look at a
  flashed board and know what firmware is on it.

### Decision: the fixes are parked

Jonathan parked them on 2026-09-03. To-do items 2, 3 and 4 of the
2026-09-02 entry are **not to be written until the fault is reported
again**, and not on anyone's own initiative. The trigger is a new report
of the symptom, and only then.

### Done the same day, from the 2026-09-02 list

Items 5, 6 and 7 — none of which depended on the recording:

- **Item 6, the COM port finds itself.** `SERIAL_PORT` ships empty; one
  USB-serial candidate is used and reported `(auto-detected)`, several are
  listed as an error, none is said plainly. An explicit port is never
  overridden, because the enumeration is not exhaustive everywhere.
  `tests/test_serial_port.py` covers the decision with no cable attached.
  This removes Notepad from the first run, which is where the partner
  actually stopped.
- **Item 5, the firmware says what it is.** Every sketch prints
  `# veleta <sketch> <version>` at boot — commaless, so a core reading that
  stream drops it — and `tests/test_version.py` now enforces all four
  copies of the number rather than three. Two kits exist and neither could
  be asked what was on it.
- **Item 7, the packaging names.** Decided: repository English, package
  Spanish, mapped by `PACKAGE_NAMES` in `scripts/build_windows_bundle.py`.
  `config.wired.env` ships as `ajustes-sensor.txt` — the extension mattered
  more than the language, since Windows hides it and a `.env` is a file the
  buyer cannot double-click. Launcher names go Spanish with it. The
  console messages stay English; translating those reaches the core's own
  output and is a bigger decision.

- **And, decided after the rename: one thing to double-click.** Everything
  that is not a sensor launcher moved into `diagnostico/` — the demo, the
  port list, the demo's config and its recording. The root of the wired
  package now holds `veleta-sensor.bat`, `ajustes-sensor.txt`, the README
  and the guide. The failure being aimed at is not a wrong setting, it is
  opening the wrong file, and that one looks to the buyer like a broken
  product. Removing the demo outright was considered and rejected: it is
  the only way to tell "the core never reaches Blender" apart from "the
  sensor is broken" without being in the room, which is the question this
  very entry had to answer blind.

- **The two zips are named after what they are.** They used to be
  `veleta-core-wired-<v>-win64.zip` and `veleta-<v>.zip` — two names
  separated by a suffix, where the 30 KB one read like the main product.
  The guide had to warn "do not confuse it with the other". Now
  `veleta-programa-<v>-windows-x64.zip` and
  `veleta-extension-blender-<v>.zip`, with `Guia-de-instalacion.pdf` loose
  beside them — three files on the media and no nesting, because a guide
  reachable only by first unzipping the thing it explains is no guide.
  Blender installs by the manifest `id`, never by the filename, so the
  extension's name was free to change.
- **And the combined package is gone** (Jonathan, same day). A customer
  buys one kit, so there is one package per sensor path and nothing that
  builds a mixture. Only `cable` is buildable: Bluetooth and WiFi each need
  a README describing only their own path, and `check()` refuses until one
  exists. The BLE wheel list is untouched and still pinned — it is what a
  Bluetooth package will need.

The rename exposed a live bug on the way through: `veleta-core.bat` named
no config and worked only through the search order finding `config.env`
beside it. Nothing ships under that name any more, so it would have run on
the built-in defaults — silently, exactly as the rule in `CLAUDE.md`
predicts. It names `ajustes-wifi.txt` now.

### Still unknown

- Whether the first sensor is actually faulty. It has not been retested in
  isolation, and presumably still exists.
- All four questions at the end of the 2026-09-02 entry are still
  unanswered (`AXIS_MAP` / `SIGN_*`, the console click, how long the
  session ran, the Blender version). The `AXIS_MAP` one is now about a
  second mounting as well as the first.

---

## 2026-09-02 — the wired kit installed on the partner's Windows PC

Reported by the partner, not observed here. Everything below that is not
marked CONFIRMED is a hypothesis to test with the recording asked for in
"What is needed to close this".

### What worked

- The wired Windows package installed and ran on a second Windows machine —
  a different one from the 2026-08-27 attempt.
- **The extension ran inside Blender for the first time.** Until this
  session `blender/__init__.py`, the manifest and the panel had never been
  executed: only `client.py` and `axes.py` were covered by tests. It
  installed, connected to the core and drove an object. The status line in
  `CLAUDE.md` has been updated accordingly.
- The whole chain therefore ran end to end on Windows for the first time:
  sketch → USB serial → core → UDP → extension → scene.
- No WiFi and no BLE were involved. The `bleak` / WinRT half of the product
  is still untouched from Windows, exactly as before.

### CONFIRMED: Blender's rotation mode is Quaternion WXYZ, and it is automatic

`blender/__init__.py:82` sets `obj.rotation_mode = "QUATERNION"` on every
frame before writing `rotation_quaternion`. So:

- Quaternion WXYZ appearing in the Transform panel is the extension's doing,
  not something the user must set.
- Setting the object back to Euler XYZ by hand does not stick: the next tick
  (~1 ms) puts it back. That is deliberate — the quaternion is what avoids
  gimbal lock.
- Consequence worth knowing: keyframes, drivers or constraints acting on the
  object's *euler* rotation are ignored while Veleta is connected.

### CONFIRMED: the wired board is running the right sketch

The question was whether it mattered that no sketch was flashed for this
session and the board kept "the last one we made".

It does not, and the proof is that it worked at all. Had the board been
running `mpu_ble_hm10.ino`, the frames would go out of D2/D3 to the HM-10
and USB would carry only the boot banner
(`mpu_ble_hm10: HM-10 on (2,3) @38400, 40 Hz`), which the core drops for
having fewer than `MIN_FIELDS` comma-separated fields. Nothing would ever
have moved. Frames arriving over USB means `mpu_serial_bridge.ino`, which is
the correct sketch and needs no change — the same one validated on the bench
on 2026-08-24 at 39 Hz.

**But the question exposed a real gap:** the firmware carries no version
number anywhere. `tests/test_version.py` checks three copies (`VERSION`,
`blender_manifest.toml`, `blender/__init__.py`) and the firmware is not one
of them, despite the "firmware, core and extension share one version"
rule in `CLAUDE.md`. There is currently no way to look at a flashed board
and know what is on it. See the to-do list.

### UNRESOLVED: an object that turned on its own for a few seconds, then stopped

Symptom, in the partner's words: the first tests went fine, then suddenly
the object began to rotate for several seconds without anyone touching the
sensor, and then stopped, apparently holding the new position.

**It is yaw. That is not a guess about the cause, it is a property of the
design.** Roll and pitch are anchored to gravity by the accelerometer
(`fusion.py`, `ALPHA_ROLL_PITCH=0.98`): however far they are pushed, they
return on their own within about a second. Yaw is pure gyro integration
(`fusion.py:79`) and an MPU-6500 has no magnetometer, so **any yaw error is
permanent and accumulates**. "Turns by itself and then stays there" is the
signature of the one axis that has no absolute reference. Whatever the root
cause, it entered through yaw.

Candidate causes, most likely first:

1. **A burst of corrupt frames.** `mpu_serial_bridge.ino:78` never checks
   that `Wire.requestFrom` actually returned 14 bytes. An I2C hiccup — a
   loose Dupont wire on a breadboard, which is exactly what moving the kit
   to another machine produces — shifts the byte alignment and the gyro
   fields come out as garbage, up to the ±250 °/s full scale. And nothing
   downstream stops it: `frames.py` accepts any line with six numeric
   fields, with no range check at all. Integrating 200 °/s for two seconds
   *is* "it spun for a few seconds and stopped". This is the same failure
   already documented for BLE in `CLAUDE.md` ("the debris still parses as
   six numeric fields") — the wired path simply has no guard against it
   either.
2. **A badly estimated gyro bias.** The first 50 frames after the core
   starts (`GYRO_CALIB_SAMPLES`, ~1.3 s at 39 Hz) must be with the sensor
   completely still, or the residual integrates. This produces *continuous*
   drift rather than a burst, so it fits the description less well — but it
   costs nothing to rule out and should be ruled out first.
3. **Thermal drift.** MPU-6500 clones move their bias while warming up over
   the first minutes. A bias captured cold is wrong once warm.
4. **`dt` comes from arrival time at the PC, not from the sensor**
   (`engine.py:81`, with no upper clamp). If Windows freezes the process,
   the frame after the stall carries the whole gap as its `dt`. Note the
   specific Windows trap: **clicking inside the console window of a `.bat`
   freezes the process** under QuickEdit mode until a key is pressed. Ask
   the partner whether they clicked in the console.

Workaround for the partner in the meantime: the panel's **Recenter** button
exists precisely for this — it re-zeroes yaw and the session continues.

### What is needed to close this

A recording of the fault. The core records raw frames and the `.bat` passes
its arguments straight through:

```
veleta-core-wired.bat --record C:\path\session.jsonl
```

Reproduce the fault with that running and bring the `.jsonl` back. Replayed
here with `--play`, the four candidates look nothing like each other:
out-of-range garbage (cause 1) versus smooth constant drift (causes 2 and 3)
versus a single frame carrying a multi-second `dt` (cause 4) are trivially
distinguishable in the raw data. Patching before seeing it is guessing.

Note that `core/tools/` does **not** ship in the Windows bundle
(`scripts/build_windows_bundle.py`), so `read_serial.py` is not available on
the partner's machine. `--record` is the diagnostic that is.

### Packaging friendliness: the names are not the problem

The partner asked whether the `.bat` and `.env` names should be friendlier,
and whether it is worth it if this becomes an executable later.

Recommendation: **do not spend effort on the names, spend it on removing the
step where the user edits a file.** If this becomes a single `.exe` the
`.bat` names disappear, but "which COM port is mine?" does not — and that is
where the partner actually stopped (steps 2 and 3 of FIRST RUN in
`README-wired.txt`: open `config.wired.env` in Notepad, type `COM5`).

In order of return:

1. **Auto-detect the serial port.** `pyserial` is already in the bundle and
   `list_ports` is already used by `list-ports.bat`. When `SERIAL_PORT` is
   unset or does not exist, enumerate the USB-serial ports: exactly one
   candidate → use it and say so on screen; several → list them and exit.
   This removes Notepad from the first run entirely.
2. **Rename in the package, not in the repository.**
   `scripts/build_windows_bundle.py:217` already maps a source path to a
   name inside the package, so the package can ship `sensor-settings.txt`
   while the repository keeps `config.wired.env`. On Windows, with file
   extensions hidden by default, `.env` is a file the buyer does not know
   how to open.
3. **Spanish `.bat` names are a decision, not a technical question.** They
   conflict with the repository's "everything in English except the
   installation guide" rule. The rule's stated reason for that one exception
   — "it is what the buyer reads" — applies just as well to a file the buyer
   double-clicks. If wanted, it resolves the same way as point 2: English in
   the repository, Spanish at packaging time.

### To do next session, in order

1. Get the `.jsonl` recording of the fault and identify the cause. Nothing
   below this line should be written before that is read.
2. **Plausibility filter in the core.** Reject a frame whose accelerometer
   magnitude is far from 1 g or whose gyro exceeds full scale, and count the
   rejections so the console says it is happening. This is the fix for
   cause 1 and it protects the BLE path equally.
3. **Check `Wire.requestFrom`'s return value** in `mpu_serial_bridge.ino`
   and skip the frame rather than emit a misaligned one. Same for
   `mpu_ble_hm10.ino`.
4. **Clamp `dt`** in `engine.py:81`. A gap of several seconds is a stall,
   not a measurement, and integrating it is never right.
5. **Version banner in the firmware.** One line at boot, e.g.
   `# veleta wired 0.1.0` — no commas, so the core drops it via `MIN_FIELDS`
   and nothing downstream needs to change. Then extend
   `tests/test_version.py` to cover the sketches, which is what the
   "three copies" rule always meant.
6. **Auto-detect the COM port** (packaging point 1 above).
7. Decide the packaging-name questions (points 2 and 3 above).

### Still unknown after this session — ask the partner

- Which Blender version was used, and whether the extension was installed
  from the zip or from a folder.
- Whether `AXIS_MAP` / `SIGN_*` had to be touched to make the object move
  the right way, or whether the identity defaults were left alone. This is
  the first real mounting the product has ever seen, so the answer resolves
  known uncertainty 2 in `CLAUDE.md` — but only if it is asked before
  anyone changes anything.
- Whether the console window was clicked (the QuickEdit stall, cause 4).
- How long the session ran before the fault appeared, which separates
  thermal drift from the rest.
