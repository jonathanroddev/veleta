#!/usr/bin/env python3
"""Build the Windows package of the veleta core.

    python3 scripts/build_windows_bundle.py [--path cable] [--out DIR]

WHAT THIS PRODUCES
    dist/veleta-programa-<version>-windows-x64.zip — the core, plus its own
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

# pyserial, the core's one non-stdlib dependency. It is pure Python — no
# compiled extension anywhere in it — so the wheel unpacks straight into the
# package and a Windows build still needs no Windows machine. Pinned by hash
# for the same reason the interpreter is.
#
# It ships even though the WiFi kit does not need it: `SOURCE=serial` covers
# the USB bench and any classic Bluetooth module, which pairs as a virtual
# COM port. Leaving it out makes those paths silently impossible in a package
# that otherwise looks complete.
SERIAL_VERSION = "3.5"
SERIAL_WHEEL = f"pyserial-{SERIAL_VERSION}-py2.py3-none-any.whl"
SERIAL_URL = ("https://files.pythonhosted.org/packages/07/bc/"
              "587a445451b253b285629263eb51c2d8e9bcea4fc97826266d186f96f558/"
              + SERIAL_WHEEL)
SERIAL_SHA256 = ("c4451db6ba391ca6ca299fb3ec7bae67a5c55dde170964c7a14ceefec02f"
                 "2cf0")

# --- BLE (`--source ble`), the battery path -------------------------------
# Eleven wheels, ~1.4 MiB, built for this exact interpreter (cp313 /
# win_amd64). They can be FETCHED from macOS but never EXERCISED there: the
# WinRT backend is a different implementation from the CoreBluetooth one the
# BLE source is developed against, so the first real test of this half
# happens on Windows. `winrt-runtime` carries its own msvcp140.dll, so no
# Visual C++ redistributable is needed.
#
# typing_extensions is here because `winrt-runtime` requires it on EVERY
# Python version, not just the old ones. Reading bleak's own metadata is not
# enough to find that: bleak asks for it only below 3.12, so on the 3.13
# interpreter this bundle ships it looks unnecessary and is not. Leaving it
# out cost a whole trip to the test machine — `import bleak` died on the
# first line, before the radio was ever touched.
#
# Pinned by version AND hash for the same reason the interpreter is.
BLE_WHEELS = (
    ("bleak-3.0.2-py3-none-any.whl",
     "https://files.pythonhosted.org/packages/26/54/05aceb9cd80073805b3ed8522e3196e8cb22f70e741873fa51406c31f4e7/bleak-3.0.2-py3-none-any.whl",
     "39092feb9e83f1df5ad2f88e837723c7211c982ce9e9cda6235104bc2ebe0d0d"),
    ("winrt_runtime-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/aa/24/2b6e536ca7745d788dfd17a2ec376fa03a8c7116dc638bb39b035635484f/winrt_runtime-3.2.1-cp313-cp313-win_amd64.whl",
     "3c1fdcaeedeb2920dc3b9039db64089a6093cad2be56a3e64acc938849245a6d"),
    ("winrt_windows_devices_bluetooth-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/05/6d/f60588846a065e69a2ec5e67c5f85eb45cb7edef2ee8974cd52fa8504de6/winrt_windows_devices_bluetooth-3.2.1-cp313-cp313-win_amd64.whl",
     "6703dfbe444ee22426738830fb305c96a728ea9ccce905acfdf811d81045fdb3"),
    ("winrt_windows_devices_bluetooth_advertisement-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/86/83/503cf815d84c5ba8c8bc61480f32e55579ebf76630163405f7df39aa297b/winrt_windows_devices_bluetooth_advertisement-3.2.1-cp313-cp313-win_amd64.whl",
     "b66410c04b8dae634a7e4b615c3b7f8adda9c7d4d6902bcad5b253da1a684943"),
    ("winrt_windows_devices_bluetooth_genericattributeprofile-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/5b/3b/eb9d99b82a36002d7885206d00ea34f4a23db69c16c94816434ded728fa3/winrt_windows_devices_bluetooth_genericattributeprofile-3.2.1-cp313-cp313-win_amd64.whl",
     "8d8d89f01e9b6931fb48217847caac3227a0aeb38a5b7782af71c2e7b262ec30"),
    ("winrt_windows_devices_enumeration-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/70/de/f30daaaa0e6f4edb6bd7ddb3e058bd453c9ad90c032a4545c4d4639338aa/winrt_windows_devices_enumeration-3.2.1-cp313-cp313-win_amd64.whl",
     "6ca40d334734829e178ad46375275c4f7b5d6d2d4fc2e8879690452cbfb36015"),
    ("winrt_windows_devices_radios-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/39/c1/24cec0cc228642554b48d436a7617d7162fb952919c55fc26e2d99c310bd/winrt_windows_devices_radios-3.2.1-cp313-cp313-win_amd64.whl",
     "bf1a975f46a2aa271ffea1340be0c7e64985050d07433e701343dddc22a72290"),
    ("winrt_windows_foundation-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/ba/7f/8d5108461351d4f6017f550af8874e90c14007f9122fa2eab9f9e0e9b4e1/winrt_windows_foundation-3.2.1-cp313-cp313-win_amd64.whl",
     "6e98617c1e46665c7a56ce3f5d28e252798416d1ebfee3201267a644a4e3c479"),
    ("winrt_windows_foundation_collections-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/94/93/4f75fd6a4c96f1e9bee198c5dc9a9b57e87a9c38117e1b5e423401886353/winrt_windows_foundation_collections-3.2.1-cp313-cp313-win_amd64.whl",
     "5e12a6e75036ee90484c33e204b85fb6785fcc9e7c8066ad65097301f48cdd10"),
    ("winrt_windows_storage_streams-3.2.1-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/15/59/601724453b885265c7779d5f8025b043a68447cbc64ceb9149d674d5b724/winrt_windows_storage_streams-3.2.1-cp313-cp313-win_amd64.whl",
     "202c5875606398b8bfaa2a290831458bb55f2196a39c1d4e5fa88a03d65ef915"),
    ("typing_extensions-4.16.0-py3-none-any.whl",
     "https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl",
     "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8"),
)

# What of a wheel actually ships: the importable package, never the
# .dist-info metadata, which is for installers and nothing here installs.
# typing_extensions is one top-level module, so its entry is a whole
# filename rather than a folder.
BLE_PREFIXES = ("bleak/", "winrt/", "typing_extensions.py")

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

# The Spanish installation guide, rendered to PDF and committed. It is a
# binary and is packed verbatim: no line endings to convert and no
# VERSION_PLACEHOLDER to substitute, which is why the guide names no
# version number anywhere in its text.
GUIDE_PDF = "Guia-de-instalacion.pdf"
GUIDE_SOURCE = "guia-instalacion-es.html"

SAMPLE = os.path.join("samples", "wt901_desk_wobble.jsonl")

# What each file is called INSIDE the package. The repository stays English,
# because that is the rule for everything in it; the package is what the
# buyer double-clicks, which is the same reason the installation guide is
# the one Spanish document that ships.
#
# The extension matters as much as the language. Windows hides known
# extensions by default, so a file called `config.wired.env` is one a buyer
# cannot open by double-clicking and cannot obviously open at all — and it
# used to be step 3 of the first run. `.txt` opens in Notepad from a
# double-click.
#
# A launcher must still NAME its configuration: the search order looks for
# `config.env`, and nothing ships under that name any more, so a launcher
# that relied on the fallback would silently run on the built-in defaults.
# `DIAGNOSTICS` is a folder, not a name: everything that is not "the thing
# you run" moves into it, so the root holds one launcher, one settings file
# and the two documents. The buyer's commonest failure is not a wrong
# setting, it is opening the wrong file — and every extra .bat beside the
# right one is a chance to do that. Nothing is dropped: the demo is the
# only way to tell "the core never reaches Blender" apart from "the sensor
# is broken" without being in the room, which is exactly the question a
# remote fault report asks.
#
# No accent in the folder name on purpose: it travels through a zip onto a
# Windows filesystem, and `Guia-de-instalacion.pdf` already made that call.
DIAGNOSTICS = "diagnostico"

PACKAGE_NAMES = {
    "config.wired.env": "ajustes-sensor.txt",
    "config.env": "ajustes-wifi.txt",
    "config.ble.env": "ajustes-bluetooth.txt",
    "veleta-core-wired.bat": "veleta-sensor.bat",
    "veleta-core.bat": "veleta-sensor-wifi.bat",
    "veleta-core-ble.bat": "veleta-sensor-bluetooth.bat",
    "config.demo.env": f"{DIAGNOSTICS}/ajustes-demo.txt",
    "veleta-core-demo.bat": f"{DIAGNOSTICS}/veleta-demo.bat",
    "list-ports.bat": f"{DIAGNOSTICS}/ver-puertos.bat",
}


def packaged_as(name):
    """The name a file travels under, which is not the name it has here."""
    return PACKAGE_NAMES.get(name, name)


# One package per sensor path, and never a combined one. A customer buys a
# cable kit, or a Bluetooth one, or a WiFi one — never all three — so the
# folder they open should hold one launcher, one settings file and a README
# about the hardware in their box. A package carrying every path is a
# package where most of what the buyer sees is for somebody else's kit, and
# the commonest failure is already opening the wrong file.
#
# `cable` is the product path and takes the plain name. The other two are
# not buildable yet, and what is missing is documentation, not code: each
# needs a README describing only that path. `README.txt` in packaging/ is
# the old multi-path one, kept as their source material — shipping it
# inside a single-path package would put back exactly what this removes.
PATH_LAUNCHER = {
    "cable": "veleta-core-wired.bat",
    "bluetooth": "veleta-core-ble.bat",
    "wifi": "veleta-core.bat",
}
PATH_CONFIG = {
    "cable": "config.wired.env",
    "bluetooth": "config.ble.env",
    "wifi": "config.env",
}
PATH_README = {"cable": "README-wired.txt"}
PATH_SUFFIX = {"cable": "", "bluetooth": "-bluetooth", "wifi": "-wifi"}

# A serial port is a thing only the cable path has. `pyserial` follows it:
# BLE is not a COM port on any platform we care about, and WiFi is a socket.
PATH_NEEDS_SERIAL = {"cable"}
PATH_NEEDS_BLE = {"bluetooth"}


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


def fetch(cache_dir, name, url, expected_sha256, download=True):
    """Path to a verified third-party artifact, fetching it if needed.

    A mismatched hash is fatal, never a warning: a package that silently
    changes what it ships is not one anybody can support.
    """
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, name)
    if not os.path.isfile(path):
        if not download:
            raise FileNotFoundError(f"{path} is missing and --no-download is set")
        print(f"fetching {url}")
        with urllib.request.urlopen(url) as response, open(path, "wb") as out:
            out.write(response.read())
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != expected_sha256:
        raise ValueError(
            f"{name} hashes {digest}, expected {expected_sha256}. Refusing "
            f"to ship something other than the pinned artifact.")
    return path


def collect_core(path):
    """The core's own files, as (abs path, path inside the bundle).

    Everything here is either the core itself, the one sensor path this
    package is for, or the diagnostics folder — which every package gets,
    because "is it the sensor or the software?" is a question every buyer
    eventually asks.

    The buyer's guide is NOT in here. It ships beside the zips, not inside
    one: it is what somebody reads before they have unzipped anything.
    """
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

    # This path's own field layout. Each is a different set of IDX_*, and a
    # package carrying the wrong one reports every frame UNPARSED.
    config = PATH_CONFIG[path]
    out.append((os.path.join(ROOT, "core", config), packaged_as(config)))

    # The demo names its own layout rather than falling back to whatever
    # configuration happens to be in the package. No package carries a file
    # called config.env any more, so the search-order fallback would land it
    # on the built-in defaults.
    out.append((os.path.join(ROOT, "core", "config.demo.env"),
                packaged_as("config.demo.env")))
    out.append((os.path.join(ROOT, "LICENSE"), "LICENSE"))
    # Beside the demo that plays it, not at the root: it is the demo's data
    # and means nothing on its own.
    out.append((os.path.join(ROOT, SAMPLE),
                f"{DIAGNOSTICS}/samples/wt901_desk_wobble.jsonl"))

    extras = [PATH_LAUNCHER[path], "veleta-core-demo.bat"]
    if path in PATH_NEEDS_SERIAL:
        # Only a serial path has a COM number to go looking for.
        extras += ["list-ports.bat", "PYSERIAL-LICENSE.txt"]
    for name in extras:
        out.append((os.path.join(PACKAGING, name), packaged_as(name)))

    readme = PATH_README.get(path)
    if readme:
        out.append((os.path.join(PACKAGING, readme), "README.txt"))
    return sorted(out, key=lambda pair: pair[1])


def check(path):
    """Refuse to build something that would be wrong on arrival."""
    problems = []
    if path not in PATH_LAUNCHER:
        return [f"unknown path {path!r}"]
    if path not in PATH_README:
        problems.append(
            f"there is no README for the {path} package yet. Write one "
            f"describing only that path — packaging/windows/README.txt is "
            f"the old multi-path original to draw it from. A single-path "
            f"package must not ship a README about hardware the buyer does "
            f"not have.")
    version, package = repo_version(), package_version()
    if package is None:
        problems.append("veleta_core/__init__.py declares no __version__")
    elif package != version:
        problems.append(f"package version {package} != VERSION {version}")
    for full, arc in collect_core(path):
        if not os.path.isfile(full):
            problems.append(f"missing: {os.path.relpath(full, ROOT)}")
        # The GPL side never travels inside the proprietary package.
        if arc.split("/")[0] in ("blender", "firmware"):
            problems.append(f"{arc} does not belong in the core package")
    sample = os.path.join(ROOT, SAMPLE)
    if os.path.isfile(sample) and os.path.getsize(sample) == 0:
        problems.append(f"{SAMPLE} is empty; the demo .bat would do nothing")
    if path == "cable":
        # The guide is not inside the zip any more, but it still ships with
        # the kit, so it is still checked here: a stale guide is a silent
        # failure whichever folder it sits in.
        guide = os.path.join(PACKAGING, GUIDE_PDF)
        source = os.path.join(PACKAGING, GUIDE_SOURCE)
        if os.path.isfile(guide) and os.path.isfile(source):
            # A PDF older than the HTML it was rendered from is a guide
            # that ships without the correction someone just made to it.
            if os.path.getmtime(guide) < os.path.getmtime(source):
                problems.append(
                    f"{GUIDE_PDF} is older than {GUIDE_SOURCE}; re-render it "
                    f"(see docs/packaging.md)")
            with open(guide, "rb") as f:
                if f.read(5) != b"%PDF-":
                    problems.append(f"{GUIDE_PDF} is not a PDF")
    return problems


def _payload(full, arc, version):
    with open(full, "rb") as f:
        data = f.read()
    if arc.endswith(CRLF_SUFFIX):
        text = data.decode("utf-8").replace("\r\n", "\n")
        text = text.replace("VERSION_PLACEHOLDER", version)
        data = text.replace("\n", "\r\n").encode("utf-8")
    return data


def build(out_dir, cache_dir, download=True, path="cable"):
    version = repo_version()
    runtime = fetch(cache_dir, PY_ZIP, PY_URL, PY_SHA256, download)
    wheel = (fetch(cache_dir, SERIAL_WHEEL, SERIAL_URL, SERIAL_SHA256,
                   download) if path in PATH_NEEDS_SERIAL else None)
    ble_wheels = ([fetch(cache_dir, name, url, sha, download)
                   for name, url, sha in BLE_WHEELS]
                  if path in PATH_NEEDS_BLE else [])
    os.makedirs(out_dir, exist_ok=True)
    # The buyer reads this name before anything else in the product, and
    # reads it beside the extension's zip. "core" is our word for it, not
    # theirs, and `veleta-core-wired-<v>-win64.zip` next to `veleta-<v>.zip`
    # were two names separated by a suffix — which is why the guide had to
    # say "the small one, about 30 KB, do not confuse it with the other".
    # They now differ at the first word after the product name.
    #
    # The cable package takes the plain name because it is the product; a
    # future Bluetooth or WiFi package qualifies itself.
    stem = f"veleta-programa{PATH_SUFFIX[path]}-{version}-windows-x64"
    target = os.path.join(out_dir, stem + ".zip")
    top = stem
    listed = []

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        def add(arc, data, executable=False):
            info = zipfile.ZipInfo(posixpath.join(top, arc),
                                   date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if executable else 0o644) << 16
            zf.writestr(info, data)
            listed.append(arc)

        for full, arc in collect_core(path):
            add(arc, _payload(full, arc, version))

        # pyserial unpacks beside veleta_core, where the rewritten ._pth
        # already looks. Only the package itself: the .dist-info metadata is
        # for installers, and nothing here installs anything.
        if wheel is not None:
            with zipfile.ZipFile(wheel) as src:
                for name in sorted(src.namelist()):
                    if not name.startswith("serial/") or name.endswith("/"):
                        continue
                    add(name, src.read(name))

        # bleak, the WinRT bindings and typing_extensions unpack the same
        # way, beside veleta_core. The winrt-* wheels are one namespace
        # package split across nine distributions: they all merge into a
        # single winrt/ tree, which is why they are unpacked rather than
        # kept as wheels. The wired-only build carries none of this: it is
        # the whole point of that build.
        licences = {}
        for path in ble_wheels:
            distribution = os.path.basename(path).split("-")[0]
            with zipfile.ZipFile(path) as src:
                for name in sorted(src.namelist()):
                    if name.endswith("/"):
                        continue
                    if name.endswith("dist-info/licenses/LICENSE"):
                        licences[distribution] = src.read(name)
                    if not name.startswith(BLE_PREFIXES):
                        continue
                    add(name, src.read(name),
                        executable=name.endswith((".dll", ".pyd")))
        if "bleak" in licences:
            text = licences["bleak"].decode("utf-8").replace("\r\n", "\n")
            text += ("\n\nThe winrt-* packages are MIT licensed too "
                     "(License-Expression: MIT in each wheel's METADATA).\n")
            add("BLEAK-LICENSE.txt", text.replace("\n", "\r\n").encode("utf-8"))
        if "typing_extensions" in licences:
            # PSF, not MIT: its own file rather than a line appended to
            # bleak's.
            text = licences["typing_extensions"].decode("utf-8")
            text = text.replace("\r\n", "\n")
            add("TYPING-EXTENSIONS-LICENSE.txt",
                text.replace("\n", "\r\n").encode("utf-8"))

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

    # The guide travels BESIDE the zips, not inside one. It is what the
    # buyer reads before they have unzipped anything, and a guide that can
    # only be reached by first doing the thing it explains is no guide. It
    # is copied rather than packed, so what lands in the output folder is
    # exactly what goes on the kit's media.
    guide = None
    if path == "cable":
        guide = os.path.join(out_dir, GUIDE_PDF)
        with open(os.path.join(PACKAGING, GUIDE_PDF), "rb") as src:
            with open(guide, "wb") as dst:
                dst.write(src.read())

    with open(target, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return target, listed, digest, guide


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
    parser.add_argument("--path", default="cable",
                        choices=sorted(PATH_LAUNCHER),
                        help="which sensor path this package is for. One "
                             "package per path, never a combined one "
                             "(default: cable, the product path)")
    args = parser.parse_args(argv)

    problems = check(args.path)
    for p in problems:
        print(f"ERROR: {p}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print("checks passed")
        return 0

    target, listed, digest, guide = build(args.out, args.cache,
                                          download=not args.no_download,
                                          path=args.path)
    core = [a for a in listed
            if not a.startswith(("runtime/", "serial/") + BLE_PREFIXES)]
    print(f"{target}")
    for arc in core:
        print(f"  {arc}")
    n_serial = len([a for a in listed if a.startswith("serial/")])
    n_ble = len([a for a in listed if a.startswith(BLE_PREFIXES)])
    n_runtime = len(listed) - len(core) - n_serial - n_ble
    if n_serial:
        print(f"  serial/   ({n_serial} files, pyserial {SERIAL_VERSION})")
    if n_ble:
        print(f"  bleak/ winrt/ typing_extensions.py  ({n_ble} files, "
              f"bleak + WinRT bindings)")
    print(f"  runtime/  ({n_runtime} files, "
          f"CPython {PY_VERSION} embeddable)")
    print(f"sha256  {digest}")
    if guide:
        print(f"\n{guide}")
        print("  the buyer's guide, beside the zip and not inside it")
    print("\nUNSIGNED: Windows will warn about an unidentified publisher.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
