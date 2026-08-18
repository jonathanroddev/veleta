"""UDP sensor source — the transport of the sellable kit."""

import socket
import time

from ..frames import last_line_of


class UdpSource:
    """Non-blocking UDP socket that yields the frames waiting on it.

    UDP, never TCP: a lost frame is a lost frame and the next one carries a
    fresher pose. A retransmission would deliver a stale pose late, which
    is worse than not delivering it (docs/protocol.md).
    """

    name = "udp"

    def __init__(self, host="0.0.0.0", port=1399):
        self.host = host
        self.port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

    def describe(self):
        return f"UDP {self.host}:{self.port}"

    def poll(self, max_batch=200):
        """Drain what is pending. The cap keeps one flood from starving the
        rest of the loop; several sensors at 100 Hz stay well inside it."""
        out = []
        for _ in range(max_batch):
            try:
                data, _addr = self.sock.recvfrom(2048)
            except BlockingIOError:
                break
            except OSError:
                break
            line = last_line_of(data)
            if line:
                out.append((line, time.time()))
        return out

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
