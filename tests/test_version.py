"""Firmware, core and extension share ONE version number.

The convention is only worth having if something enforces it, because the
failure it prevents — a user running new software against old firmware —
does not show up as an error, it shows up as an object that moves wrongly.
"""

import os
import re
import unittest

import context


def read(*parts):
    with open(os.path.join(context.ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestVersionsAgree(unittest.TestCase):
    def setUp(self):
        self.declared = read("VERSION").strip()

    def test_version_file_is_sane(self):
        self.assertRegex(self.declared, r"^\d+\.\d+\.\d+$")

    def test_core_matches(self):
        from vane_core import __version__
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


if __name__ == "__main__":
    unittest.main()
