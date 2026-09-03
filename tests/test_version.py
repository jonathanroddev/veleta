"""Firmware, core and extension share ONE version number.

The convention is only worth having if something enforces it, because the
failure it prevents — a user running new software against old firmware —
does not show up as an error, it shows up as an object that moves wrongly.

The firmware was the copy nothing checked, and it was the copy with no
number in it at all: a flashed board could not say what was on it, which
is exactly the question that came up the first time a second kit existed.
Every sketch now prints `# veleta <sketch> <version>` at boot — commaless,
so the core drops the line for having fewer than MIN_FIELDS fields — and
these tests are what keep those banners from drifting.
"""

import os
import re
import unittest

import context

BANNER = re.compile(r"#\s*veleta\s+([A-Za-z0-9_]+)\s+(\d+\.\d+\.\d+)")


def read(*parts):
    with open(os.path.join(context.ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def sketches():
    """Every .ino in firmware/, as (path relative to the root, source)."""
    root = os.path.join(context.ROOT, "firmware")
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            if name.endswith(".ino"):
                full = os.path.join(folder, name)
                found.append((os.path.relpath(full, context.ROOT),
                              open(full, encoding="utf-8").read()))
    return found


class TestVersionsAgree(unittest.TestCase):
    def setUp(self):
        self.declared = read("VERSION").strip()

    def test_version_file_is_sane(self):
        self.assertRegex(self.declared, r"^\d+\.\d+\.\d+$")

    def test_core_matches(self):
        from veleta_core import __version__
        self.assertEqual(__version__, self.declared)

    def test_manifest_matches(self):
        manifest = read("blender", "blender_manifest.toml")
        found = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M)
        self.assertIsNotNone(found, "no version in blender_manifest.toml")
        self.assertEqual(found.group(1), self.declared)

    def test_extension_module_matches(self):
        source = read("blender", "__init__.py")
        found = re.search(r'^VERSION\s*=\s*"([^"]+)"', source, re.M)
        self.assertIsNotNone(found, "no VERSION in blender/__init__.py")
        self.assertEqual(found.group(1), self.declared)


class TestFirmwareVersions(unittest.TestCase):
    """The third copy of the number, and the one hardest to look up: it is
    on a board, not on a disk."""

    def setUp(self):
        self.declared = read("VERSION").strip()
        self.sketches = sketches()

    def test_there_are_sketches_to_check(self):
        """A moved or renamed firmware/ must fail loudly rather than leave
        every test below passing over an empty list."""
        self.assertGreater(len(self.sketches), 0, "no .ino found in firmware/")

    def test_every_sketch_prints_a_version_banner(self):
        for path, source in self.sketches:
            with self.subTest(sketch=path):
                self.assertRegex(source, BANNER,
                                 f"{path} prints no '# veleta <name> "
                                 f"<version>' banner")

    def test_every_banner_matches_the_declared_version(self):
        for path, source in self.sketches:
            with self.subTest(sketch=path):
                for _, version in BANNER.findall(source):
                    self.assertEqual(version, self.declared)

    def test_the_banner_names_its_own_sketch(self):
        """`# veleta mpu_ble_hm10 0.1.0` on a board flashed with the wired
        sketch would be worse than no banner at all."""
        for path, source in self.sketches:
            with self.subTest(sketch=path):
                expected = os.path.splitext(os.path.basename(path))[0]
                names = [name for name, _ in BANNER.findall(source)]
                self.assertIn(expected, names)

    def test_no_banner_carries_a_comma(self):
        """A line with commas in it is a frame as far as the core is
        concerned, and a banner that parses is a banner that moves an
        object."""
        for path, source in self.sketches:
            with self.subTest(sketch=path):
                for line in source.splitlines():
                    if BANNER.search(line):
                        self.assertNotIn(",", line.split("#", 1)[1],
                                         f"{path}: banner contains a comma")


if __name__ == "__main__":
    unittest.main()
