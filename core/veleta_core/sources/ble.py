"""BLE sensor source — the transport of the battery-powered kit.

This is the only place in the product that imports `bleak`, and it is
reached only through `open_ble_source()`, exactly as `pyserial` is reached
only through `open_serial_source()`. A user of the WiFi kit never installs
it.

WHY A THREAD. `bleak` is asyncio and the core's loop is a dull synchronous
drain (see `__main__`). Rather than colour the whole core async for one
transport, the BLE client lives in its own thread with its own event loop
and hands frames over a queue. `poll()` then looks like every other
source's, and nothing above this file knows BLE is asynchronous.

WHY NO deviceId ON THE WIRE. One BLE connection carries exactly one
sensor, so the transport is the identity — the same argument the wired
bench makes (docs/protocol.md). The device is named from the peripheral's
advertised BLE name, which is set once with `AT+NAME`. Spending ~7 bytes
per frame on a constant string would cost real frames per second: the link
carries about 1990 B/s and nothing more.
"""

import queue
import threading
import time

# The HM-10's transparent-UART service and characteristic. They are the
# module's identity as much as its name is: a BLE peripheral exposing
# 0xFFE0/0xFFE1 is an HM-10 or a clone of one.
HM10_SERVICE = "0000ffe0-0000-1000-8000-00805f9b34fb"
HM10_CHAR = "0000ffe1-0000-1000-8000-00805f9b34fb"


class LineAssembler:
    """Turns a stream of 20-byte BLE notifications back into whole lines.

    Separated from the client so it can be tested without a radio: the
    reassembly is where the subtle bugs live, not in the connecting.

    The first chunk after connecting is almost never a frame boundary, so
    everything before the first newline is discarded. That matters more
    here than it looks: a truncated frame can still carry six numeric
    fields — a cut "-0.3044" arrives as "44" — and would be parsed as a
    real reading rather than rejected.
    """

    def __init__(self):
        self.buf = b""
        self.synced = False

    def feed(self, data):
        """Add a chunk, return the complete lines it finished (as str)."""
        self.buf += bytes(data)
        if not self.synced:
            _head, sep, rest = self.buf.partition(b"\n")
            if not sep:
                return []
            self.buf = rest
            self.synced = True
        out = []
        while b"\n" in self.buf:
            raw, _, self.buf = self.buf.partition(b"\n")
            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                out.append(line)
        return out


class BleSource:
    """Notifications from one BLE peripheral, drained like any other source.

    Raises from the constructor if the peripheral cannot be found or
    connected, so `__main__` reports it the same way it reports a missing
    serial port.
    """

    name = "ble"

    def __init__(self, name=None, address=None, char=HM10_CHAR,
                 device_id=None, timeout=20.0, max_queue=4000):
        self.target_name = name or None
        self.target_address = address or None
        self.char = char or HM10_CHAR
        self.device_id = device_id or None
        self.timeout = float(timeout)
        self._q = queue.Queue(maxsize=int(max_queue))
        self._assembler = LineAssembler()
        self._dropped = 0
        self._ready = threading.Event()
        self._error = None
        self._loop = None
        self._stop = None
        self._thread = threading.Thread(target=self._run, name="veleta-ble",
                                        daemon=True)
        self._thread.start()
        # +10 s: the wait covers scanning AND connecting, and a BLE connect
        # is slower than anyone expects the first time.
        if not self._ready.wait(self.timeout + 10.0):
            raise RuntimeError("BLE source did not come up in time")
        if self._error is not None:
            raise self._error

    # ---- the source interface -------------------------------------------

    def describe(self):
        who = self.device_id or self.target_name or self.target_address or "?"
        return f"BLE {who} ({self.char})"

    def poll(self, max_batch=200):
        """Drain what the BLE thread has queued. Never blocks."""
        out = []
        for _ in range(max_batch):
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                break
        return out

    def close(self):
        if self._loop is not None and self._stop is not None:
            try:
                self._loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:
                pass                      # loop already gone
        self._thread.join(timeout=5.0)

    # ---- everything below runs on the BLE thread -------------------------

    def _run(self):
        import asyncio
        try:
            asyncio.run(self._main())
        except Exception as e:            # noqa: BLE001 - reported to the caller
            if self._error is None:
                self._error = e
        finally:
            self._ready.set()

    async def _main(self):
        import asyncio
        from bleak import BleakClient

        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        try:
            device = await self._find()
            async with BleakClient(device) as client:
                await client.start_notify(self.char, self._on_notify)
                if not self.device_id:
                    self.device_id = getattr(device, "name", None) or str(
                        getattr(device, "address", "ble"))
                self._ready.set()
                await self._stop.wait()
                try:
                    await client.stop_notify(self.char)
                except Exception:         # noqa: BLE001 - already going down
                    pass
        except Exception as e:            # noqa: BLE001
            self._error = e
            self._ready.set()

    async def _find(self):
        from bleak import BleakScanner

        if self.target_address:
            dev = await BleakScanner.find_device_by_address(
                self.target_address, timeout=self.timeout)
            if dev is None:
                raise RuntimeError(
                    f"no BLE peripheral at address {self.target_address}")
            return dev
        if self.target_name:
            dev = await BleakScanner.find_device_by_name(
                self.target_name, timeout=self.timeout)
            if dev is None:
                raise RuntimeError(
                    f"no BLE peripheral named {self.target_name!r}. It is not "
                    f"advertising, or something is already connected to it")
            return dev
        # Nothing configured: take the first peripheral advertising the
        # HM-10 service. Fine with one module, ambiguous with several —
        # which is why BLE_NAME exists.
        found = await BleakScanner.discover(timeout=self.timeout,
                                            return_adv=True)
        for dev, adv in found.values():
            uuids = [str(u).lower() for u in (adv.service_uuids or ())]
            if HM10_SERVICE in uuids:
                return dev
        raise RuntimeError(
            "no BLE peripheral advertising the HM-10 service "
            f"({HM10_SERVICE}) found. Set BLE_NAME if yours does not "
            f"advertise it")

    def _on_notify(self, _characteristic, data):
        """Queue whatever complete frames this notification finished."""
        now = time.time()
        for line in self._assembler.feed(data):
            try:
                self._q.put_nowait((line, now))
            except queue.Full:
                # The consumer has stalled. Drop the oldest pose, never the
                # newest: a stale pose delivered late is worse than a gap
                # (docs/protocol.md).
                try:
                    self._q.get_nowait()
                    self._q.put_nowait((line, now))
                except (queue.Empty, queue.Full):
                    pass
                self._dropped += 1
