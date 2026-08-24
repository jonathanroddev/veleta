"""Where the core takes its sensor frames from.

Four interchangeable sources, all exposing the same thing: an iterator of
(line, timestamp) pairs. The file source is what makes the whole product
demonstrable without hardware, testable in CI, and debuggable from a
recording a user sent in.
"""

from .udp import UdpSource
from .file import FileSource

__all__ = ["UdpSource", "FileSource", "open_serial_source",
           "open_ble_source"]


def open_serial_source(*args, **kwargs):
    """Import the serial source lazily.

    Only the wired bench needs `pyserial`, so importing it up front would
    make it mandatory for everyone. Kept behind a function, a user of the
    WiFi or BLE kit never has to install it.
    """
    from .serial_source import SerialSource
    return SerialSource(*args, **kwargs)


def open_ble_source(*args, **kwargs):
    """Import the BLE source lazily.

    `bleak` is the core's second non-stdlib dependency and, unlike
    `pyserial`, it is not pure Python: it is a facade over a compiled
    platform backend (pyobjc on macOS, WinRT on Windows, dbus on Linux).
    Kept behind a function, only someone running a BLE sensor pays for it.
    """
    from .ble import BleSource
    return BleSource(*args, **kwargs)
