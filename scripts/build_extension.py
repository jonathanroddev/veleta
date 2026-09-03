#!/usr/bin/env python3
"""Build the Blender extension package.

    python3 scripts/build_extension.py [--out DIR] [--check]

WHAT GOES IN, AND WHAT MUST NOT
    Only the contents of `blender/`: the manifest, the Python that imports
    `bpy`, and its LICENSE. The core never travels inside this zip. It
    would technically fit — packaged as a wheel, say — but the moment it
    ships inside the extension it is being distributed as part of a GPL
    work, and that dissolves the licence separation the whole product is
    arranged around. The extension consumes the core over the network; it
    does not carry it.

REPRODUCIBLE
    Same commit in, byte-identical zip out: entries are sorted, timestamps
    are fixed and permissions are normalised. Without that, "the zip I
    uploaded" and "the zip I can rebuild" are not verifiably the same
    thing, and there is no way to answer a user reporting a fault in a
    build you no longer have.
"""

import argparse
import hashlib
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "blender")

# A fixed timestamp, not "now": the zip must not change because the clock
# did. 1980-01-01 is the earliest a zip entry can carry.
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

EXCLUDE_NAMES = {"__pycache__", ".DS_Store", ".git"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".orig", ".rej")


def repo_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def manifest_version():
    path = os.path.join(SOURCE, "blender_manifest.toml")
    with open(path, encoding="utf-8") as f:
        found = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
    return found.group(1) if found else None


def collect():
    """Every file that belongs in the package, sorted, as (abs, arcname)."""
    out = []
    for folder, dirs, files in os.walk(SOURCE):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_NAMES)
        for name in sorted(files):
            if name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(folder, name)
            out.append((full, os.path.relpath(full, SOURCE)))
    return sorted(out, key=lambda pair: pair[1])


def check():
    """Refuse to build something that would be wrong on arrival."""
    problems = []
    version, manifest = repo_version(), manifest_version()
    if manifest is None:
        problems.append("blender_manifest.toml declares no version")
    elif manifest != version:
        problems.append(f"manifest version {manifest} != VERSION {version}")
    if not os.path.isfile(os.path.join(SOURCE, "LICENSE")):
        problems.append("blender/LICENSE is missing (the GPL text must ship)")
    demo = os.path.join(SOURCE, "demo", "desk_wobble.jsonl")
    if not os.path.isfile(demo) or os.path.getsize(demo) == 0:
        # Without it the Play demo button is dead, and the extension does
        # nothing at all for anyone who does not own a kit.
        problems.append("blender/demo/desk_wobble.jsonl is missing or empty")
    names = [arc for _full, arc in collect()]
    if "blender_manifest.toml" not in names:
        problems.append("blender_manifest.toml must sit at the zip root")
    for arc in names:
        # Nothing from the proprietary side may have wandered in.
        if arc.split(os.sep)[0] in ("core", "firmware", "veleta_core"):
            problems.append(f"{arc} does not belong in the extension package")
    return problems


def build(out_dir):
    version = repo_version()
    os.makedirs(out_dir, exist_ok=True)
    # `veleta-<version>.zip` read like the main product beside the core's
    # zip, when it is the 30 KB half. The name says what it is now. Blender
    # installs by the manifest `id`, never by the filename, so this is free
    # to be readable.
    target = os.path.join(out_dir,
                          f"veleta-extension-blender-{version}.zip")
    entries = collect()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, arc in entries:
            info = zipfile.ZipInfo(arc, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as f:
                zf.writestr(info, f.read())
    with open(target, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return target, entries, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"),
                        help="where to write the zip (default: dist/)")
    parser.add_argument("--check", action="store_true",
                        help="run the checks and build nothing")
    args = parser.parse_args(argv)

    problems = check()
    for p in problems:
        print(f"ERROR: {p}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print("checks passed")
        return 0

    target, entries, digest = build(args.out)
    print(f"{target}")
    for _full, arc in entries:
        print(f"  {arc}")
    print(f"sha256  {digest}")
    print("\nValidate it with Blender before uploading:")
    print(f"  blender --command extension validate {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
