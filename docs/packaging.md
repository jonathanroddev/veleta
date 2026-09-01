# Packaging and distribution

Distributable artifacts, and none of them is built by hand.

| Artifact | Built by | Goes to |
|---|---|---|
| Extension package (`veleta-<version>.zip`) | `scripts/build_extension.py` | The Blender extensions platform, and the kit as an offline copy |
| Core package, one per OS (`veleta-core-<version>-win64.zip`) | `scripts/build_windows_bundle.py` — Windows only so far | The download page, and the kit |
| Wired-only core package (`veleta-core-wired-<version>-win64.zip`) | the same script, `--wired-only` | The wired kit — **this is what v1 ships** |

## Versioning

Firmware, core and extension **share one version number** and are released
together. There is no per-component versioning.

The number lives in `VERSION` at the repository root. Three places must
agree with it, and `tests/test_version.py` fails the build when they do
not:

- `core/veleta_core/__init__.py` → `__version__`
- `blender/blender_manifest.toml` → `version`
- `blender/__init__.py` → `VERSION`

The extension asks the core for its version when it connects and warns, in
the panel, when they disagree. Old firmware against new software is the
commonest fault in a product like this and is miserable to diagnose from
the symptoms alone.

## Building the extension package

```bash
python3 scripts/build_extension.py            # writes dist/veleta-<version>.zip
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
blender --command extension validate dist/veleta-<version>.zip
```

> Never run: there is no Blender on the development machine. This is the
> first thing to do on a machine that has one.

## The core package

One per operating system, shipped with the kit and served from the download
page. **Windows exists; macOS and Linux do not yet.**

```bash
python3 scripts/build_windows_bundle.py                # dist/veleta-core-<v>-win64.zip
python3 scripts/build_windows_bundle.py --wired-only   # dist/veleta-core-wired-<v>-win64.zip
python3 scripts/build_windows_bundle.py --check        # checks only, builds nothing
```

### Two builds, and why the small one is the one that ships

**The cable is the product path for v1**, so there is a package that carries
that path and nothing else. `--wired-only` leaves out `config.env` (the WiFi
layout), `config.ble.env`, `veleta-core.bat`, `veleta-core-ble.bat` and all
eleven bleak/WinRT wheels. What is left is the core, pyserial, the
interpreter, and a launcher that reads `config.wired.env`.

Two reasons, and the second is the real one:

- **Size and simplicity.** Nothing in the package points at a path the buyer
  did not buy, so there is no wrong `.bat` to double-click and no second
  config file to edit by mistake.
- **It carries nothing unproven.** The BLE half of the full package rests on
  wheels with a compiled WinRT backend that has still never been exercised on
  a Windows machine. The wired package cannot fail that way because it does
  not contain it.

The full build still exists and still builds; it gains the wired `.bat` too.
It is the package for a kit that is not the wired one. **`sources/ble.py`
travels in both** — it is standard-library-clean and imports `bleak` lazily,
so it costs nothing in the wired package and there is no build that has to
strip source files out of the core.

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
`veleta-core-wired-<versión>-win64.zip` and leaves it there. And it ships
**only in the wired build**: in the full package it would be instructions
for hardware the buyer might not have.

This is the one place Spanish is correct inside the repository. The rest —
code, comments, the other READMEs, this document — stays in English.

**There are two READMEs, and the buyer only ever sees one.** `README.txt` is
the full package's. `README-wired.txt` is the wired package's and is packed
**under the name `README.txt`**, so that buyer reads a document that
describes only the path they have, with no branches for hardware that is not
in the box. The cost is that a change to what both describe — the firewall,
the version handshake, the licence list — has to be made in both files;
nothing enforces that.

`veleta-core-demo.bat` passes `--config config.demo.env`, and that file
ships in both packages. It used to pass no `--config` at all: in the full
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

**Bluetooth Low Energy is a different matter.** A BLE module is not a serial
port on any platform we care about, so it needed a new source rather than a
config change — `core/veleta_core/sources/ble.py`, on `bleak`. That is why
`bleak` and its WinRT bindings are eleven pinned wheels rather than one pure
Python file, why they are unpacked rather than kept as wheels (nine of them
merge into a single `winrt/` namespace tree), and why the full package is the
larger and less proven of the two. Read the BLE section of
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
2. Bump `VERSION`, and the three places listed above with it.
3. Update `CHANGELOG.md`.
4. `python3 scripts/build_extension.py` and record the sha256.
5. `blender --command extension validate` on the zip.
6. Build and sign the core packages — `--wired-only` for the wired kit,
   the full build for any other, both recorded by sha256.
7. Flash and verify the firmware at that version on real hardware.
8. Publish the release; point the download page's batch mapping at it.
