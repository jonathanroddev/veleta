#!/usr/bin/env python3
"""Build the Windows package of the veleta core.

    python3 scripts/build_windows_bundle.py [--out DIR] [--check]

WHAT THIS PRODUCES
    dist/veleta-core-<version>-win64.zip — the core, plus its own private
    copy of Python. The user unzips it and double-clicks a .bat: nothing is
    installed, nothing is written outside the folder, and the machine's
    PATH is neither read nor changed. Deleting the folder removes it.

    It is UNSIGNED, and says so in its README. Windows will warn about an
    unidentified publisher until the release build carries a code-signing
    certificate — see docs/packaging.md. That makes this a build for
    machines you control, not one to hand to a customer.

WHY A PRIVATE RUNTIME AND NOT A FROZEN .EXE
    The core is standard library only, so the official embeddable Python
    build runs it as it is. That buys three things a PyInstaller-style
    executable does not: it can be assembled on any operating system, so a
    Windows machine is not needed to produce a Windows package; there is no
    frozen binary for antivirus heuristics to quarantine, which is a
    routine problem for unsigned single-file executables; and what ships is
    plainly the code in this repository rather than a black box.

    The cost is that the core ships as readable .py files. For a test build
    that is fine. If the release is meant to be opaque, that is a decision
    to take deliberately later — not a reason to change this now.

WHAT MUST NOT BE IN IT
    Nothing from `blender/`. That directory is GPL v3 or later, and putting
    it inside a proprietary package is the mirror image of the mistake
    `build_extension.py` exists to prevent. The two travel separately and
    meet over the documented protocol.

REPRODUCIBLE
    Same commit and same pinned runtime in, byte-identical zip out: entries
    sorted, timestamps fixed, permissions normalised, sha256 printed. The
    runtime is pinned by version AND by hash, so a silently republished
    upstream file fails the build instead of changing the product.
"""

import argparse
import hashlib
import os
import posixpath
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGING = os.path.join(ROOT, "packaging", "windows")

# The embeddable CPython build that goes inside the package. Pinned by hash
# as well as by version: python.org republishes nothing, but a package that
# silently changes what interpreter it ships is not one you can support.
PY_VERSION = "3.13.11"
PY_ZIP = f"python-{PY_VERSION}-embed-amd64.zip"
PY_URL = f"https://www.python.org/ftp/python/{PY_VERSION}/{PY_ZIP}"
PY_SHA256 = "1ec066fb61ba5e8c73e29e048cd07c26850f74585e3a116005135b31b8004890"
PY_TAG = "python" + "".join(PY_VERSION.split(".")[:2])   # -> python313

# The embeddable build's ._pth is what its interpreter uses instead of the
# usual sys.path machinery. The stock one exposes only the runtime folder,
# so `..` is added: that is the bundle root, where veleta_core sits.
PTH_CONTENT = f"{PY_TAG}.zip\n.\n..\n"

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store", ".git"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".orig", ".rej")

# Windows reads these with a text editor, so they go in with CRLF. Keeping
# them LF in the repository is what .gitattributes is for.
CRLF_SUFFIX = (".bat", ".txt", ".env")

SAMPLE = os.path.join("samples", "wt901_desk_wobble.jsonl")


def repo_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def package_version():
    path = os.path.join(ROOT, "core", "veleta_core", "__init__.py")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def runtime_zip(cache_dir, download=True):
    """Path to the verified embeddable runtime, fetching it if needed."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, PY_ZIP)
    if not os.path.isfile(path):
        if not download:
            raise FileNotFoundError(f"{path} is missing and --no-download is set")
        print(f"fetching {PY_URL}")
        with urllib.request.urlopen(PY_URL) as response, \
                open(path, "wb") as out:
            out.write(response.read())
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != PY_SHA256:
        raise ValueError(
            f"{PY_ZIP} hashes {digest}, expected {PY_SHA256}. Refusing to "
            f"ship an interpreter that is not the pinned one.")
    return path


def collect_core():
    """The core's own files, as (abs path, path inside the bundle)."""
    out = []
    source = os.path.join(ROOT, "core", "veleta_core")
    for folder, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_NAMES)
        for name in sorted(files):
            if name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, source).replace(os.sep, "/")
            out.append((full, f"veleta_core/{rel}"))
    out.append((os.path.join(ROOT, "core", "config.env"), "config.env"))
    out.append((os.path.join(ROOT, "LICENSE"), "LICENSE"))
    out.append((os.path.join(ROOT, SAMPLE), "samples/wt901_desk_wobble.jsonl"))
    for name in ("veleta-core.bat", "veleta-core-demo.bat", "README.txt"):
        out.append((os.path.join(PACKAGING, name), name))
    return sorted(out, key=lambda pair: pair[1])


def check():
    """Refuse to build something that would be wrong on arrival."""
    problems = []
    version, package = repo_version(), package_version()
    if package is None:
        problems.append("veleta_core/__init__.py declares no __version__")
    elif package != version:
        problems.append(f"package version {package} != VERSION {version}")
    for full, arc in collect_core():
        if not os.path.isfile(full):
            problems.append(f"missing: {os.path.relpath(full, ROOT)}")
        # The GPL side never travels inside the proprietary package.
        if arc.split("/")[0] in ("blender", "firmware"):
            problems.append(f"{arc} does not belong in the core package")
    sample = os.path.join(ROOT, SAMPLE)
    if os.path.isfile(sample) and os.path.getsize(sample) == 0:
        problems.append(f"{SAMPLE} is empty; the demo .bat would do nothing")
    return problems


def _payload(full, arc, version):
    with open(full, "rb") as f:
        data = f.read()
    if arc.endswith(CRLF_SUFFIX):
        text = data.decode("utf-8").replace("\r\n", "\n")
        text = text.replace("VERSION_PLACEHOLDER", version)
        data = text.replace("\n", "\r\n").encode("utf-8")
    return data


def build(out_dir, cache_dir, download=True):
    version = repo_version()
    runtime = runtime_zip(cache_dir, download=download)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, f"veleta-core-{version}-win64.zip")
    top = f"veleta-core-{version}-win64"
    listed = []

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        def add(arc, data, executable=False):
            info = zipfile.ZipInfo(posixpath.join(top, arc),
                                   date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if executable else 0o644) << 16
            zf.writestr(info, data)
            listed.append(arc)

        for full, arc in collect_core():
            add(arc, _payload(full, arc, version))

        with zipfile.ZipFile(runtime) as src:
            for name in sorted(src.namelist()):
                if name.endswith("/"):
                    continue
                arc = f"runtime/{name}"
                if name == f"{PY_TAG}._pth":
                    # Rewritten so the interpreter can see the bundle root.
                    add(arc, PTH_CONTENT.encode("ascii"))
                    continue
                add(arc, src.read(name),
                    executable=name.endswith((".exe", ".dll", ".pyd")))

    with open(target, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return target, listed, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"),
                        help="where to write the zip (default: dist/)")
    parser.add_argument("--cache", default=os.path.join(ROOT, "build"),
                        help="where the runtime is kept (default: build/)")
    parser.add_argument("--check", action="store_true",
                        help="run the checks and build nothing")
    parser.add_argument("--no-download", action="store_true",
                        help="fail instead of fetching the runtime")
    args = parser.parse_args(argv)

    problems = check()
    for p in problems:
        print(f"ERROR: {p}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print("checks passed")
        return 0

    target, listed, digest = build(args.out, args.cache,
                                   download=not args.no_download)
    core = [a for a in listed if not a.startswith("runtime/")]
    print(f"{target}")
    for arc in core:
        print(f"  {arc}")
    print(f"  runtime/  ({len(listed) - len(core)} files, "
          f"CPython {PY_VERSION} embeddable)")
    print(f"sha256  {digest}")
    print("\nUNSIGNED: Windows will warn about an unidentified publisher.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
