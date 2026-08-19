"""UDP client for the veleta core.

Deliberately free of `bpy`: everything in this file can be exercised
without Blender, which is where the awkward parts live — the subscription
renewal, the version handshake, non-blocking reads. The Blender-facing
code that uses it is in `__init__.py`.

The extension never starts, bundles or distributes the core. It talks to a
process the user already has, over the documented protocol, and that is
what keeps the two on different licences (see the repository README).
"""

import json
import socket
import time


class CoreClient:
    """A subscription to a running core.

    The core streams poses to whoever asked for them and forgets a
    subscriber that stops renewing, so a Blender that crashes or a scene
    that is closed does not leave the core talking to nobody.
    """

    def __init__(self, host="127.0.0.1", port=1400, ttl=10.0):
        self.host = host
        self.port = int(port)
        self.ttl = float(ttl)
        self.sock = None
        self.hello = None
        self._next_renew = 0.0

    # ---------- lifecycle ----------
    def connect(self, timeout=1.0):
        """Subscribe and return the core's hello, or raise.

        The hello carries the core's version, which is what the version
        check is built on: firmware, core and extension ship together, so a
        mismatch means the user updated one of the three and not the rest.
        """
        self.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        payload = json.dumps({"cmd": "subscribe", "ttl": self.ttl})
        self.sock.sendto(payload.encode("utf-8"), (self.host, self.port))
        data, _addr = self.sock.recvfrom(8192)
        self.hello = json.loads(data.decode("utf-8"))
        self.sock.setblocking(False)
        self._next_renew = time.time() + self.ttl / 2.0
        return self.hello

    def close(self):
        if self.sock is not None:
            try:
                self.sock.sendto(json.dumps({"cmd": "unsubscribe"}).encode(),
                                 (self.host, self.port))
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self.hello = None

    @property
    def connected(self):
        return self.sock is not None

    # ---------- traffic ----------
    def poll(self, max_batch=200):
        """Return the pose messages waiting on the socket.

        Renews the subscription halfway through its life, so a dropped
        renewal datagram still has a second chance before the core forgets
        this consumer.
        """
        if self.sock is None:
            return []
        now = time.time()
        if now >= self._next_renew:
            self._renew(now)
        poses = []
        for _ in range(max_batch):
            try:
                data, _addr = self.sock.recvfrom(8192)
            except (BlockingIOError, socket.timeout):
                break
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8", errors="ignore"))
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("type") == "pose":
                poses.append(msg)
        return poses

    def _renew(self, now=None):
        now = now or time.time()
        try:
            self.sock.sendto(
                json.dumps({"cmd": "subscribe", "ttl": self.ttl}).encode(),
                (self.host, self.port))
        except OSError:
            pass
        self._next_renew = now + self.ttl / 2.0

    def command(self, cmd, **kwargs):
        """Send a command and wait briefly for its reply.

        Used for calibrate/recenter/devices, which are user actions: a
        short blocking wait is fine there and the reply is what the panel
        reports back. The pose stream is never read this way.
        """
        if self.sock is None:
            return None
        msg = {"cmd": cmd}
        msg.update(kwargs)
        try:
            self.sock.sendto(json.dumps(msg).encode("utf-8"),
                             (self.host, self.port))
        except OSError as e:
            return {"ok": False, "error": str(e)}
        deadline = time.time() + 0.5
        while time.time() < deadline:
            try:
                data, _addr = self.sock.recvfrom(8192)
            except (BlockingIOError, socket.timeout):
                time.sleep(0.005)
                continue
            except OSError as e:
                return {"ok": False, "error": str(e)}
            try:
                reply = json.loads(data.decode("utf-8", errors="ignore"))
            except ValueError:
                continue
            if isinstance(reply, dict) and reply.get("type") != "pose":
                return reply
        return {"ok": False, "error": "the core did not answer"}


def version_warning(extension_version, hello):
    """Compare versions and return a message, or None when they agree.

    Firmware, core and extension share one version number on purpose. The
    commonest fault in a product like this is a user who updated one piece
    and not the others, and it is miserable to diagnose from the symptoms
    alone — so it is stated plainly, in the panel, on connecting.
    """
    if not hello:
        return None
    core_version = str(hello.get("version", "unknown"))
    if core_version == str(extension_version):
        return None
    return (f"Version mismatch: core {core_version}, extension "
            f"{extension_version}. They ship together — update the one "
            f"that is behind.")
