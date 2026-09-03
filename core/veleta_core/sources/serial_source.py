"""Serial sensor source — the wired bench.

This is the only place in the product that imports `pyserial`, and it is
reached only through `open_serial_source()`. Before the core existed this
import lived inside Blender, which meant installing a package into
Blender's own bundled Python — a genuinely awkward step that the split
removes.

It also picks the port when nobody has said which one. Typing a COM number
into a configuration file is where a first run actually stops, and the
number cannot be guessed or documented: Windows assigns it, and pairing a
Bluetooth module often creates two ports where only one works.
"""

import time

import serial  # noqa: F401  (imported lazily by sources/__init__.py)

# Shipped configurations used to carry a made-up port so the key had a
# visible shape. A configuration that was never edited therefore names a
# device that does not exist, so the placeholder means "not set" too.
PLACEHOLDER = "CHANGE_ME"


class SerialPortError(Exception):
    """No port could be chosen or opened. The message lists what was seen."""


def list_candidates():
    """Serial ports worth offering, ordered by device name.

    A port with a USB vendor id is something a person plugged in; COM1 on a
    desktop machine and macOS's Bluetooth-Incoming-Port are not. The filter
    is dropped rather than allowed to empty the list, because a paired
    classic Bluetooth module is a supported sensor and its virtual COM port
    carries no vendor id of its own.
    """
    from serial.tools import list_ports
    ports = sorted(list_ports.comports(), key=lambda p: p.device)
    usb = [p for p in ports if getattr(p, "vid", None) is not None]
    return usb or ports


def _catalogue(candidates):
    """The ports, one per line, for an error message."""
    if not candidates:
        return "    (no serial ports are visible at all)"
    lines = []
    for port in candidates:
        label = (getattr(port, "description", "") or "").strip()
        lines.append(f"    {port.device}"
                     + (f"    {label}" if label and label != "n/a" else ""))
    return "\n".join(lines)


def _catalogue_now():
    """The same, enumerated on the spot, for a failure that has no list."""
    try:
        return _catalogue(list_candidates())
    except Exception:                                # noqa: BLE001
        return "    (the port list could not be read)"


def resolve_port(requested, candidates=None):
    """Return (port, auto_detected) for a requested SERIAL_PORT value.

    An explicit port is never second-guessed, even when it is not in the
    enumeration: that list is not exhaustive on every platform, and
    overriding what somebody deliberately wrote is worse than failing to
    open it. Unset — or never edited past the placeholder — is the case
    worth solving: one candidate is the answer, and several is a question
    only the user can settle.
    """
    requested = (requested or "").strip()
    if requested and PLACEHOLDER not in requested:
        return requested, False
    if candidates is None:
        candidates = list_candidates()
    if len(candidates) == 1:
        return candidates[0].device, True
    if not candidates:
        raise SerialPortError(
            "no serial port is set and none could be found. Is the sensor "
            "plugged in? A classic Bluetooth module has to be paired first: "
            "it then appears as an ordinary serial port.")
    raise SerialPortError(
        "no serial port is set and there is more than one to choose from, "
        "so the choice is yours:\n" + _catalogue(candidates) +
        "\nSet SERIAL_PORT in the configuration, or name one explicitly.")


class SerialSource:
    name = "serial"

    def __init__(self, port, baud=115200, settle=2.0):
        self.port_name, self.auto = resolve_port(port)
        self.baud = int(baud)
        try:
            self.ser = serial.Serial(self.port_name, self.baud, timeout=0)
        except Exception as e:                       # noqa: BLE001
            raise SerialPortError(
                f"could not open {self.port_name}: {e}\n"
                f"The ports visible right now are:\n{_catalogue_now()}") from e
        if settle:
            # Opening the port resets the board; give it time to boot before
            # trusting what comes out of it.
            time.sleep(settle)
        self.ser.reset_input_buffer()
        self._buf = b""

    def describe(self):
        how = " (auto-detected)" if self.auto else ""
        return f"serial {self.port_name} @ {self.baud}{how}"

    def poll(self, max_batch=200):
        out = []
        try:
            chunk = self.ser.read(4096)
        except Exception:
            return out
        if chunk:
            self._buf += chunk
        while len(out) < max_batch and b"\n" in self._buf:
            raw, _, self._buf = self._buf.partition(b"\n")
            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                out.append((line, time.time()))
        return out

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass
