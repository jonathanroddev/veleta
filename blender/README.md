# blender — the Veleta extension

The Blender side: it connects to the [core](../core/), receives orientation
and applies it to objects in the scene.

**It is a consumer, not a driver.** It does not read sensors, does not open
serial ports and never bundles the core — it talks to a program the user
already has, over [a documented protocol](../docs/protocol.md).

## Licence

**GNU GPL v3 or later** — see [`LICENSE`](LICENSE). Different from the rest
of this repository, and deliberately so.

Blender's Python API is part of Blender and Blender is GPL, so anything
that imports `bpy` and is published has to be GPL-compatible; the
extensions platform requires it explicitly. Everything in **this directory
and only this directory** is under those terms. `core/` and `firmware/` are
proprietary and are not distributed with it.

**The rule:** the package uploaded to the platform contains only what is in
here. `scripts/build_extension.py` enforces it.

## Building the package

```bash
python3 ../scripts/build_extension.py
blender --command extension validate ../dist/veleta-extension-blender-<version>.zip
```

## What is in here

| | |
|---|---|
| `blender_manifest.toml` | Extension manifest: id, version, permissions, licence |
| `__init__.py` | Preferences, operators, panel, the `bpy.app.timers` pump |
| `client.py` | The UDP client and the version check. Imports no `bpy` |
| `axes.py` | `AXIS_MAP` / `SIGN_*`. Imports no `bpy` |
| `playback.py` | The built-in demo player. Imports no `bpy` |
| `demo/desk_wobble.jsonl` | The recording the demo replays |

## The built-in demo

The core is proprietary and ships with the kit, so without this the
extension would do nothing whatsoever for anyone who installed it from the
platform and bought nothing. **Play demo** replays a short bundled
recording against the scene: no core, no sensors, no network.

It deliberately does **not** reimplement the core. There is no fusion, no
calibration and no device routing in it — it replays angles that were
already fused, from a file we ship and whose layout we control, through the
same `_apply_angles()` the live stream uses. If the demo ever needs to grow
a filter, that is the signal it has stopped being a demo.

`client.py`, `axes.py` and `playback.py` are free of `bpy` on purpose: they hold the parts
that are awkward to get right — subscription renewal, the version
handshake, axis permutation — and that keeps them testable outside Blender,
which matters because there is no Blender on the development machine.
`tests/test_protocol.py` and `tests/test_axes.py` exercise them for real.

## Conventions

- **Never block the interface.** Everything runs on `bpy.app.timers`. This
  rule predates the extension and survives it.
- **Configuration lives in Blender's preferences**, not in a `config.env`.
  An installed extension's files are replaced on update, so a config file
  inside the package is a file the user edits and then loses.
- **A wrong-looking axis is a configuration change**, never a code change.
  That is what `AXIS_MAP` and `SIGN_*` are for.
- **The extension is a package now**, not a self-contained script. The
  old "one loose file" rule was about Blender's text editor, where
  `__file__` often does not exist. It does not apply to an installed
  extension and should not be reintroduced.
