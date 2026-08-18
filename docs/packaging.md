# Packaging and distribution

Two distributable artifacts, and neither is built by hand.

| Artifact | Built by | Goes to |
|---|---|---|
| Extension package (`vane-<version>.zip`) | `scripts/build_extension.py` | The Blender extensions platform, and the kit as an offline copy |
| Core installer, one per OS | Not built yet — see below | The download page, and the kit |

## Versioning

Firmware, core and extension **share one version number** and are released
together. There is no per-component versioning.

The number lives in `VERSION` at the repository root. Three places must
agree with it, and `tests/test_version.py` fails the build when they do
not:

- `core/vane_core/__init__.py` → `__version__`
- `blender/blender_manifest.toml` → `version`
- `blender/__init__.py` → `VERSION`

The extension asks the core for its version when it connects and warns, in
the panel, when they disagree. Old firmware against new software is the
commonest fault in a product like this and is miserable to diagnose from
the symptoms alone.

## Building the extension package

```bash
python3 scripts/build_extension.py            # writes dist/vane-<version>.zip
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
blender --command extension validate dist/vane-<version>.zip
```

> Never run: there is no Blender on the development machine. This is the
> first thing to do on a machine that has one.

## The core installer

Not built yet. One per operating system, shipped with the kit and served
from the download page.

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
