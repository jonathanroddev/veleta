"""Where the core takes its sensor frames from.

Three interchangeable sources, all exposing the same thing: an iterator of
(line, timestamp) pairs. The file source is what makes the whole product
demonstrable without hardware, testable in CI, and debuggable from a
recording a user sent in.
"""

from .udp import UdpSource
from .file import FileSource

__all__ = ["UdpSource", "FileSource", "open_serial_source"]


def open_serial_source(*args, **kwargs):
    """Import the serial source lazily.

    `pyserial` is the core's only non-stdlib dependency and only the wired
    bench needs it, so importing it up front would make it mandatory for
    everyone. Kept behind a function, a user of the WiFi kit never has to
    install it.
    """
    from .serial_source import SerialSource
    return SerialSource(*args, **kwargs)
