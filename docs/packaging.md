# Packaging and distribution

Distributable artifacts, and none of them is built by hand.

| Artifact | Built by | Goes to |
|---|---|---|
| Cable core package (`veleta-programa-<version>-windows-x64.zip`) | `scripts/build_windows_bundle.py` | The cable kit — **this is what v1 ships** |
| Extension package (`veleta-extension-blender-<version>.zip`) | `scripts/build_extension.py` | The Blender extensions platform, and the kit as an offline copy |
| The buyer's guide (`Guia-de-instalacion.pdf`) | rendered by hand from the HTML; the build copies it | Beside the two zips, never inside one |

**Three files on the kit's media, and no nesting.** The guide is what
somebody reads before they have unzipped anything, so a guide reachable
only by first doing the thing it explains is no guide.

## Versioning

Firmware, core and extension **share one version number** and are released
together. There is no per-component versioning.

The number lives in `VERSION` at the repository root. Four places must
agree with it, and `tests/test_version.py` fails the build when they do
not:

- `core/veleta_core/__init__.py` → `__version__`
- `blender/blender_manifest.toml` → `version`
- `blender/__init__.py` → `VERSION`
- **every sketch in `firmware/`** → a boot banner, `# veleta <sketch>
  <version>`

The firmware was the copy nothing checked, which meant a flashed board
could not be asked what was on it — the question that comes up the moment
a second kit exists. Each sketch now prints its name and version once at
boot. The line carries **no comma**, so a core reading that stream drops it
for having fewer than `MIN_FIELDS` fields; on the wired path the core
usually never sees it at all, because opening the port resets the board and
`SerialSource` flushes what arrives while it settles. The banner is for
whoever opens a serial monitor, and the test is what stops it drifting.

The extension asks the core for its version when it connects and warns, in
the panel, when they disagree. Old firmware against new software is the
commonest fault in a product like this and is miserable to diagnose from
the symptoms alone.

## Building the extension package

```bash
python3 scripts/build_extension.py     # dist/veleta-extension-blender-<v>.zip
python3 scripts/build_extension.py --check    # checks only, builds nothing
```

**Only the contents of `blender/`** go in: the manifest, the Python that
imports `bpy`, and the GPL text. The script refuses to build if anything
from `core/` or `firmware/` has wandered in.

The core is left out even though it would technically fit — packaged as a
wheel, for instance. The moment it ships inside the extension it is being
distributed as part of a GPL work, and that dissolves the licence
separation the product is arranged around. The extension consumes the core
over the network; it never carries it.

**The build is reproducible**: entries sorted, timestamps fixed,
permissions normalised, so the same commit produces a byte-identical zip
and the script prints its sha256. Without that, "the zip I uploaded" and
"the zip I can rebuild" are not verifiably the same artifact, and a user
reporting a fault in a build you no longer have is unanswerable.

Before uploading, validate with Blender itself:

```bash
blender --command extension validate dist/veleta-extension-blender-<v>.zip
```

> Never run: there is no Blender on the development machine. This is the
> first thing to do on a machine that has one.

## The core package

One per operating system, shipped with the kit and served from the download
page. **Windows exists; macOS and Linux do not yet.**

```bash
python3 scripts/build_windows_bundle.py                    # the cable package
python3 scripts/build_windows_bundle.py --check            # checks only
python3 scripts/build_windows_bundle.py --path bluetooth   # not yet buildable
```

### One package per sensor path, and never a combined one

**A customer buys one kit.** Cable now, Bluetooth or WiFi later — never all
three at once. So a package carries one sensor path and nothing else: one
launcher, one settings file, one README about the hardware in the box.

A package carrying every path is a package where most of what the buyer
sees belongs to somebody else's kit, and the commonest failure is already
opening the wrong file. There used to be a combined build behind
`--wired-only`'s absence; it is gone. `--path` selects, and there is
nothing to select that produces a mixture.

Two more things fall out of it, and the second is the real one:

- **Size.** The cable package carries no `bleak` and no WinRT wheels, so it
  is about a megabyte smaller and has nothing to go wrong in a dependency
  the buyer's path does not use.
- **It carries nothing unproven.** The BLE half rests on wheels with a
  compiled WinRT backend that has still never been exercised on a Windows
  machine. The cable package cannot fail that way because it does not
  contain it.

**`sources/ble.py` travels in every package** — it is standard-library-clean
and imports `bleak` lazily, so it costs nothing where it is unused and no
build has to strip source files out of the core.

**Only `cable` can be built today, and what is missing is documentation,
not code.** A Bluetooth or WiFi package needs a README describing only that
path; `check()` refuses the build and says so. `packaging/windows/README.txt`
is the old multi-path README, kept as the source material to write them
from — shipping it inside a single-path package would put back exactly what
this split removes.

### What is in it, and why it is not a frozen .exe

The core plus its own private copy of CPython — the official embeddable
build, pinned by version **and by sha256**. The user unzips it and
double-clicks a `.bat`; nothing is installed, nothing is written outside the
folder, `PATH` is neither read nor changed, and deleting the folder removes
it.

The core is standard library only, so the embeddable runtime runs it as it
is. That buys three things a PyInstaller-style executable does not:

- **It can be assembled on any operating system.** Producing the Windows
  package does not need a Windows machine, which matters when there isn't
  one. The build is reproducible on the same terms as the extension: sorted
  entries, fixed timestamps, byte-identical zip, sha256 printed.
- **There is no frozen binary for antivirus heuristics to quarantine.**
  Unsigned single-file executables get flagged routinely, and that is a
  worse first impression than a folder of plain files.
- **What ships is visibly the code in this repository**, not a black box.

The cost is that the core ships as readable `.py` files. For a test build
that is fine. If a release is meant to be opaque, decide that deliberately —
it is not a reason to change this now.

`packaging/windows/` holds the `.bat` launchers and the READMEs that go in.
They are LF in the repository and converted to CRLF when packed, and
`VERSION_PLACEHOLDER` in them is replaced with the release version as they
are packed.

There is one launcher per path — `veleta-core-wired.bat`,
`veleta-core-ble.bat`, `veleta-core.bat` for WiFi — plus `list-ports.bat` and
`veleta-core-demo.bat`, which replays the bundled sample on a loop so the
whole chain — core, protocol, extension, scene — can be checked on a machine
that has no sensor anywhere near it.

### The names change on the way in

**The repository is English; the package is what the buyer double-clicks.**
`PACKAGE_NAMES` in `scripts/build_windows_bundle.py` maps one to the other,
the same way `README-wired.txt` already ships as `README.txt`:

| In the repository | In the package |
|---|---|
| `core/config.wired.env` | `ajustes-sensor.txt` |
| `core/config.env` | `ajustes-wifi.txt` |
| `core/config.ble.env` | `ajustes-bluetooth.txt` |
| `veleta-core-wired.bat` | `veleta-sensor.bat` |
| `veleta-core.bat` | `veleta-sensor-wifi.bat` |
| `veleta-core-ble.bat` | `veleta-sensor-bluetooth.bat` |
| `core/config.demo.env` | `diagnostico/ajustes-demo.txt` |
| `veleta-core-demo.bat` | `diagnostico/veleta-demo.bat` |
| `list-ports.bat` | `diagnostico/ver-puertos.bat` |
| `samples/wt901_desk_wobble.jsonl` | `diagnostico/samples/…` |

Two separate reasons, and neither is decoration.

**The extension, first.** Windows hides known extensions by default, so
`config.wired.env` is a file the buyer cannot open with a double-click and
cannot obviously open at all — and editing it used to be step 3 of the first
run. `.txt` opens in Notepad. This is the half that was actually costing
support.

**The language, second.** It resolves the same way the installation guide
does: the rule is English everywhere in the repository, and the stated
reason for the guide's exception — *it is what the buyer reads* — applies
just as well to a file the buyer double-clicks. So the Spanish exists only
at packing time, and nothing in the repository changes name.

Consequences worth knowing. A `.bat`'s own comments and console messages
name their **package** siblings, because that is the folder they run in —
reading them in the repository means reading names that only exist after
packing. And a launcher must now **name its configuration explicitly**: the
search order looks for a file called `config.env`, nothing ships under that
name any more, and `veleta-core.bat` was the one launcher still relying on
that fallback. It would have quietly dropped onto the built-in defaults,
which is precisely the failure the "every shipped launcher names its config"
rule exists to prevent.

The console messages inside the launchers are still English. Translating
those is a separate decision and a larger one — it reaches the core's own
output, not just the packaging.

### One thing to double-click

Everything that is not a sensor launcher goes into `diagnostico/`, so the
root of the wired package holds exactly one program a buyer would open:

```
veleta-sensor.bat        <- the only thing to run
ajustes-sensor.txt
README.txt
Guia-de-instalacion.pdf
diagnostico/             <- veleta-demo.bat, ver-puertos.bat,
                            ajustes-demo.txt, samples/
runtime/  veleta_core/
```

The failure this is aimed at is not a wrong setting, it is **opening the
wrong file** — every extra `.bat` beside the right one is a chance to do
that, and it is a failure that looks like the product being broken.

**Nothing was dropped, and the demo in particular must not be.** It is the
only way to tell "the core never reaches Blender" apart from "the sensor is
broken" without being in the room, which is exactly what a remote fault
report asks — see `docs/fieldnotes.md` for the session where that question
had to be answered blind. Together with the extension's own "Play demo"
button, which needs no core at all, the two split the chain three ways:
extension only, everything-but-the-sensor, and the sensor.

The two launchers that moved are one level down, so they reach the
interpreter through `..\runtime\python.exe`, and the demo's recording moved
with it: `samples/` is the demo's data and means nothing beside a launcher
that does not read it.

### The buyer's guide is a PDF, in Spanish, and it is committed

`packaging/windows/Guia-de-instalacion.pdf` travels inside the wired
package. It is the document the buyer actually reads: Spanish, A4, four
pages, covering only the cable path — unzip, find the COM port, install the
extension, first run, what to check when nothing moves.

It is **rendered from `packaging/windows/guia-instalacion-es.html`** and both
files are committed. The build packs the PDF verbatim and never generates
it, which keeps the byte-identical guarantee and keeps the build free of a
PDF toolchain. To change the guide, edit the HTML and re-render:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=packaging/windows/Guia-de-instalacion.pdf \
  file://$PWD/packaging/windows/guia-instalacion-es.html
```

`--check` fails when the PDF is older than the HTML, because the failure it
is guarding against is silent: a correction made to the source and never
rendered ships as the uncorrected guide, and nothing about the zip looks
wrong.

Two consequences worth knowing. **The guide names no version number**, since
a PDF cannot carry `VERSION_PLACEHOLDER` through the packing step — it says
`veleta-programa-<versión>-windows-x64.zip` and leaves it there. And it ships
**only with the cable kit**: it describes the cable path, and beside a
Bluetooth or WiFi package it would be instructions for hardware the buyer
does not have. It is **not inside the zip** — the build copies it into the
output folder beside it, so what lands there is what goes on the media.

This is the one place Spanish is correct inside the repository. The rest —
code, comments, the other READMEs, this document — stays in English.

**There are two READMEs, and the buyer only ever sees one.** `README.txt` is
the old multi-path one, now unshipped and kept only as source material.
`README-wired.txt` is the cable package's and is packed **under the name
`README.txt`**, so that buyer reads a document describing only the path
they have, with no branches for hardware that is not in the box. When a
Bluetooth or WiFi package arrives it gets its own the same way, and the
cost is that a change to what they all describe — the firewall, the version
handshake, the licence list — has to be made in each; nothing enforces
that.

`veleta-core-demo.bat` passes `--config ajustes-demo.txt` — the packed name
of `config.demo.env` — and that file ships in both packages. It used to pass no `--config` at all: in the full
package it then read `config.env`, and in the wired package — which carries
no `config.env` — it fell back to the built-in `DEFAULTS`, which happen to
be the WT901 layout the bundled recording uses. It worked on that
coincidence, and changing `DEFAULTS` or re-recording the sample from another
sensor would have broken the one thing a buyer runs before their hardware
does, silently and with every frame reported UNPARSED.

The demo now names its layout like every other path. `tests/test_playback.py`
replays every recording in `samples/` through `config.demo.env` rather than
through `DEFAULTS`, so a sample that drifts from it fails the suite.

**pyserial is bundled**, pinned by hash like the interpreter. It is pure
Python — no compiled extension anywhere in it — so it unpacks straight into
the package and the build still needs no Windows machine.

It ships even though the WiFi kit does not need it, because `SOURCE=serial`
is not only the USB bench: **a classic Bluetooth module is a serial link
over the air**, and pairing one creates a virtual COM port that the existing
`SerialSource` reads without a line of new code. Leaving pyserial out made
that path silently impossible in a package that otherwise looked complete.

`list-ports.bat` runs `serial.tools.list_ports`, which is how the COM number
of a paired module is found — Windows assigns it, and pairing often creates
two ports where only the outgoing one works.

**The core now finds that port itself when it can.** An unset `SERIAL_PORT`
— or one still holding the shipped `CHANGE_ME` placeholder — means "find
it": exactly one USB-serial candidate is used and reported as
`(auto-detected)`, several are listed as an error, none is said plainly. An
explicit port is never second-guessed, even when it is absent from the
enumeration, because that list is not exhaustive on every platform.

The candidate filter prefers ports carrying a USB vendor id — COM1 on a
desktop and macOS's `Bluetooth-Incoming-Port` are not sensors — but never
lets that empty the list, because a paired classic Bluetooth module has no
vendor id of its own and is a supported sensor. `tests/test_serial_port.py`
covers the decision without a cable; `list-ports.bat` survives as the
diagnostic for the ambiguous case.

**Bluetooth Low Energy is a different matter.** A BLE module is not a serial
port on any platform we care about, so it needed a new source rather than a
config change — `core/veleta_core/sources/ble.py`, on `bleak`. That is why
`bleak` and its WinRT bindings are eleven pinned wheels rather than one pure
Python file, why they are unpacked rather than kept as wheels (nine of them
merge into a single `winrt/` namespace tree), and why a Bluetooth package
will be the larger and less proven one when it exists. Read the BLE section of
`scripts/build_windows_bundle.py` before touching that list.

### The firewall, which is not a footnote

On first run Windows asks whether to allow the core on the network. Blocked,
sensor frames never arrive and **the only symptom is that nothing moves** —
no error, anywhere. It is the most common thing to go wrong on a fresh
Windows machine, so it is called out in the package README rather than left
to a support conversation.

Only the sensor port is exposed; the consumer port stays on `127.0.0.1`.

This is a WiFi-kit problem. A wired or BLE sensor does not reach the core
over the network at all, so the wired package should never need the prompt
for the sensor — but say "allow on private networks" if it appears anyway,
rather than teaching the buyer to reason about which case they are in.

### Signing

The part with the most hidden work in the whole product, which is why it is
written down long before it is due.

- **macOS** — the binary must be signed with an Apple Developer certificate
  and pass **notarisation**. Without it the system blocks the app and the
  user sees an alarming warning.
- **Windows** — without a code-signing certificate, **SmartScreen** warns.
  That warning is a common reason a customer concludes the software is
  malicious and asks for a refund.

Both certificates are paid and annual. This does not have to be solved
before the repository exists, but it does have to be solved **before the
first pre-sale**.

Until then the Windows package is an **unsigned test build**: fine for a
machine you control, not for a customer. It says so in its own README.

The name on the certificate is what the customer reads while installing, so
it should match the structure that sells the kit, not a personal name.

## Getting the software to the buyer

The kit carries **no physical media**. It carries a printed card with a QR
code pointing at a **short URL under our control**, and that URL redirects
to the **installation guide** — never straight to a binary, so the
destination can change without reprinting cards.

- The download page serves the version matching the **batch** of the kit.
- **No registration, no email.** The software without the hardware only
  replays sample recordings, so a signup wall would cost conversions and
  support without protecting anything.
- Artifacts are published as **releases of this repository**.
- The **batch number is visible on the device label**, so support knows
  which version is in front of them.
- If a batch ever needs a recall notice, that is an opt-in notification
  list — never a wall in front of the download.

## Release checklist

1. `python3 -m unittest discover -s tests -t tests` — all green.
2. Bump `VERSION`, and the four places listed above with it — the
   firmware banners included.
3. Update `CHANGELOG.md`.
4. `python3 scripts/build_extension.py` and record the sha256.
5. `blender --command extension validate` on the zip.
6. Build and sign the core package for each kit being shipped — one
   `--path` per kit, never a combined one — recorded by sha256, plus the
   guide beside them.
7. Flash and verify the firmware at that version on real hardware.
8. Publish the release; point the download page's batch mapping at it.
