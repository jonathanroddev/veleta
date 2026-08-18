"""The core <-> consumers half of the protocol.

One UDP socket does both jobs: it takes commands from consumers and it
streams poses back to whoever asked for them.

WHY SUBSCRIPTION AND NOT A CONFIGURED DESTINATION
    A consumer sends {"cmd": "subscribe"} and the core streams to the
    address that datagram came from, for SUBSCRIPTION_TTL seconds, renewed
    by subscribing again. So the core needs no IP configured, two consumers
    can watch at once (Blender and a diagnostic tool), and a consumer that
    dies simply stops being sent to. The version handshake and the
    calibration commands ride the same socket, which means a consumer that
    can talk to the core can always ask it what version it is.

Everything is one JSON object per datagram. See docs/protocol.md.
"""

import json
import socket
import time

from . import PROTOCOL_VERSION, __version__


class Server:
    def __init__(self, host, port, engine, ttl=10.0, log=None):
        self.engine = engine
        self.ttl = float(ttl)
        self.host = host
        self.port = int(port)
        self._log = log or (lambda msg: None)
        self.subscribers = {}   # (host, port) -> expiry timestamp
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        # Port 0 means "any free port"; record the one actually granted so
        # callers (and the tests) can find it.
        self.port = self.sock.getsockname()[1]
        self.sock.setblocking(False)

    def describe(self):
        return f"UDP {self.host}:{self.port}"

    # ---------- commands ----------
    def poll(self, max_batch=50):
        """Handle pending commands. Never raises: a malformed datagram from
        the network must not be able to stop the core."""
        for _ in range(max_batch):
            try:
                data, addr = self.sock.recvfrom(4096)
            except BlockingIOError:
                break
            except OSError:
                break
            try:
                reply = self._dispatch(data, addr)
            except Exception as e:      # noqa: BLE001 - deliberate catch-all
                reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            if reply is not None:
                self._send(reply, addr)

    def _dispatch(self, data, addr):
        try:
            msg = json.loads(data.decode("utf-8", errors="ignore"))
        except ValueError:
            return {"ok": False, "error": "not JSON"}
        if not isinstance(msg, dict):
            return {"ok": False, "error": "expected a JSON object"}
        cmd = str(msg.get("cmd", "")).strip().lower()

        if cmd == "hello":
            return self._hello()
        if cmd == "subscribe":
            ttl = float(msg.get("ttl", self.ttl))
            self.subscribers[addr] = time.time() + max(1.0, ttl)
            reply = self._hello()
            reply["subscribed"] = True
            reply["ttl"] = max(1.0, ttl)
            return reply
        if cmd == "unsubscribe":
            self.subscribers.pop(addr, None)
            return {"ok": True, "subscribed": False}
        if cmd == "calibrate":
            return {"ok": True, "calibrated": self.engine.calibrate()}
        if cmd == "recenter":
            device = str(msg.get("device", ""))
            ok = self.engine.recenter(device)
            return {"ok": ok, "device": device,
                    "error": None if ok else "unknown device or no data yet"}
        if cmd == "devices":
            return {"ok": True, "devices": self.engine.device_list()}
        return {"ok": False, "error": f"unknown command: {cmd!r}"}

    def _hello(self):
        return {
            "ok": True,
            "type": "hello",
            "version": __version__,
            "protocol": PROTOCOL_VERSION,
            "devices": self.engine.device_list(),
        }

    # ---------- streaming ----------
    def broadcast(self, pose):
        """Send one pose to every live subscriber, dropping expired ones."""
        if not self.subscribers:
            return
        now = time.time()
        expired = [a for a, exp in self.subscribers.items() if exp <= now]
        for a in expired:
            del self.subscribers[a]
        if not self.subscribers:
            return
        payload = dict(pose.as_dict())
        payload["type"] = "pose"
        for a in list(self.subscribers):
            self._send(payload, a)

    def _send(self, obj, addr):
        try:
            self.sock.sendto(json.dumps(obj).encode("utf-8"), addr)
        except OSError:
            pass  # a consumer that went away is not the core's problem

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
