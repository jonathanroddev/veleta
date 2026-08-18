#!/usr/bin/env python3
"""
read_udp.py — UDP diagnostic reader.

Listens on a UDP port and dumps what the WiFi sensors send. Use it to
VERIFY the real CSV format — field order, column count, terminator —
BEFORE trusting the core with it.

Each line is shown twice: the raw text exactly as it arrived, and what the
indices in your config.env make of it. When those two disagree, the fix is
config.env, never the parser.

No external dependencies: standard library only.

Usage:
    python3 tools/read_udp.py [PORT] [SECONDS] [HOST]

Defaults: port 1399, 8 s, host 0.0.0.0 (all interfaces).

What to look for:
    - Does each line start with the DeviceID (something like 'WT53...')?
    - How many comma-separated fields are there?
    - Does the interpretation line show the angles where you expect them?
    - Any UNPARSED lines? Then your IDX_* do not match this sensor.
"""
import socket
import sys
import time

import _diag

port = int(sys.argv[1]) if len(sys.argv) > 1 else 1399
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
host = sys.argv[3] if len(sys.argv) > 3 else "0.0.0.0"

layout, cfg_path = _diag.load_layout()
print(f"[read_udp] Listening on UDP {host}:{port} for {secs}s...", flush=True)
print(f"[read_udp] Interpreting with: {cfg_path or 'built-in defaults'}",
      flush=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((host, port))
sock.settimeout(0.5)

summary = _diag.Summary(layout)
t_end = time.time() + secs
while time.time() < t_end:
    try:
        data, addr = sock.recvfrom(2048)
    except socket.timeout:
        continue
    text = data.decode("utf-8", errors="ignore").strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    summary.note_batch(len(lines))
    for line in lines:
        reading = summary.note(line)
        n_fields = len(line.split(","))
        print(f"[{addr[0]}] fields={n_fields:2d} | {line}", flush=True)
        print(f"{' ' * (len(addr[0]) + 2)}          -> {reading}", flush=True)

sock.close()
summary.report("[read_udp]")
