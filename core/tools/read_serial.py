#!/usr/bin/env python3
"""
read_serial.py — Serial diagnostic reader for the wired bench.

Opens the port, resets the board via DTR and dumps what comes out. Useful
for the I2C diagnostics sketch and for checking the raw CSV before trusting
the core with it.

Each data line is shown twice: the raw text as it arrived, and what the
indices in your config.env make of it. Anything that is not a data line —
the I2C sketch's own output, boot messages — is passed through untouched.

Usage:
    python3 tools/read_serial.py [PORT] [SECONDS] [BAUD]

PORT is required in practice: the Arduino Nano reaches the PC through a
USB-serial chip, so its name (/dev/cu.wchusbserial*, /dev/cu.usbserial-*,
/dev/ttyUSB0...) depends on the machine. Find it with `ls /dev/cu.*`.

Defaults: 8 s, 115200 baud. Needs pyserial.
"""
import sys
import time

import serial

import _diag

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.wchusbserial-CHANGE_ME"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
baud = int(sys.argv[3]) if len(sys.argv) > 3 else 115200

# The wired frames carry no DeviceID — a cable is one sensor, so the
# transport is the identity. The core names it from SERIAL_DEVICE_ID; here
# it is only a label for the interpretation line.
layout, cfg_path = _diag.load_layout()

print(f"[read_serial] Opening {port} @ {baud} for {secs}s...", flush=True)
print(f"[read_serial] Interpreting with: {cfg_path or 'built-in defaults'}",
      flush=True)
ser = serial.Serial(port, baud, timeout=0.2)

# Reset via DTR (a DTR pulse resets the MCU -> re-runs setup(); works the
# same on the Nano's CH340/FTDI as on a board with native USB)
ser.setDTR(False)
time.sleep(0.1)
ser.setDTR(True)
time.sleep(0.2)
ser.reset_input_buffer()

summary = _diag.Summary(layout, default_device="wired")
t_end = time.time() + secs
while time.time() < t_end:
    line = ser.readline().decode("utf-8", errors="ignore").rstrip("\r\n")
    if not line:
        continue
    print(line, flush=True)
    if "," in line:      # anything else is the sketch talking, not a frame
        print(f"    -> {summary.note(line)}", flush=True)

ser.close()
summary.report("[read_serial]")
