"""Import paths for the tests.

`core/` and `blender/` are two separately licensed components that never
import each other at runtime, so there is no package that spans both. The
tests are the one place that looks at both, and this is where that is made
explicit rather than repeated in every file.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for path in (os.path.join(ROOT, "core"), os.path.join(ROOT, "blender")):
    if path not in sys.path:
        sys.path.insert(0, path)
