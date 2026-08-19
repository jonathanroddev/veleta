# Packaging and distribution

Two distributable artifacts, and neither is built by hand.

| Artifact | Built by | Goes to |
|---|---|---|
| Extension package (`veleta-<version>.zip`) | `scripts/build_extension.py` | The Blender extensions platform, and the kit as an offline copy |
| Core package, one per OS (`veleta-core-<version>-win64.zip`) | `scripts/build_windows_bundle.py` — Windows only so far | The download page, and the kit |

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
python3 scripts/build_windows_bundle.py            # dist/veleta-core-<v>-win64.zip
python3 scripts/build_windows_bundle.py --check    # checks only, builds nothing
```

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

`packaging/windows/` holds the two `.bat` files and the README that go in.
They are LF in the repository and converted to CRLF when packed.

The second `.bat` replays the bundled sample on a loop, so the whole chain —
core, protocol, extension, scene — can be checked on a machine that has no
sensor anywhere near it.

**pyserial is not bundled**, so `SOURCE=serial` fails inside this package.
The wired bench is a development path, not a customer one; the WiFi kit does
not need it.

### The firewall, which is not a footnote

On first run Windows asks whether to allow the core on the network. Blocked,
sensor frames never arrive and **the only symptom is that nothing moves** —
no error, anywhere. It is the most common thing to go wrong on a fresh
Windows machine, so it is called out in the package README rather than left
to a support conversation.

Only the sensor port is exposed; the consumer port stays on `127.0.0.1`.

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
6. Build and sign the core installers.
7. Flash and verify the firmware at that version on real hardware.
8. Publish the release; point the download page's batch mapping at it.
