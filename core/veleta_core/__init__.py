"""veleta core — sensors in, oriented poses out.

An ordinary program: it does not import `bpy` and it runs, and is useful,
with no Blender anywhere on the machine. That independence is not an
accident of design, it is what keeps the core outside the GPL that governs
the Blender extension. See the licence map in the repository README.
"""

# Firmware, core and extension share ONE version number and ship together;
# tests/test_version.py checks this against the repository's VERSION file.
# The extension asks the core for it on connecting and warns when they
# differ: old firmware against new software is the most common fault in a
# product like this one, and without the check it is miserable to diagnose.
__version__ = "0.1.0"

# Wire format version for the core <-> consumers protocol. Bumped only when
# a change would break an existing consumer.
PROTOCOL_VERSION = 1
