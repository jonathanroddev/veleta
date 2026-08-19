"""veleta core — command line entry point.

    python3 -m veleta_core                      # listen to sensors over UDP
    python3 -m veleta_core --play samples/x.jsonl --loop
    python3 -m veleta_core --record samples/new.jsonl
    python3 -m veleta_core --source serial --serial-port /dev/cu.usbserial-110

The loop is deliberately dull: drain the source, fuse, hand each pose to
the subscribers, answer any command that arrived. Nothing blocks, so a
sensor that goes quiet never leaves the process wedged.
"""

import argparse
import sys
import time

from . import __version__
from .config import load as load_config
from .engine import Engine
from .recorder import Recorder
from .server import Server
from .sources import FileSource, UdpSource, open_serial_source


def _log(msg):
    print(f"[veleta-core] {msg}", flush=True)


def build_parser():
    p = argparse.ArgumentParser(
        prog="veleta-core",
        description="Reads IMU sensors, fuses their orientation and "
                    "re-exposes it over UDP for Blender, Godot or anything "
                    "else that speaks the protocol.")
    p.add_argument("--config", metavar="PATH",
                   help="config.env to use (default: the usual search order)")
    p.add_argument("--source", choices=("udp", "serial", "file"),
                   help="where the sensor frames come from")
    p.add_argument("--listen-port", type=int,
                   help="UDP port the sensors send to")
    p.add_argument("--serial-port", help="serial device of the wired bench")
    p.add_argument("--baud", type=int, help="serial baud rate")
    p.add_argument("--control-port", type=int,
                   help="UDP port consumers connect to")
    p.add_argument("--play", metavar="FILE",
                   help="replay a .jsonl recording instead of using hardware")
    p.add_argument("--loop", action="store_true",
                   help="restart the recording when it ends")
    p.add_argument("--speed", type=float, default=1.0,
                   help="playback speed multiplier (default 1.0)")
    p.add_argument("--record", metavar="FILE",
                   help="write every incoming frame to a .jsonl recording")
    p.add_argument("--duration", type=float,
                   help="stop after N seconds (for tests and demos)")
    p.add_argument("--quiet", action="store_true",
                   help="only report errors")
    p.add_argument("--version", action="version",
                   version=f"veleta core {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    log = (lambda m: None) if args.quiet else _log

    cfg, cfg_path = load_config(args.config)
    log(f"veleta core {__version__}")
    log(f"config: {cfg_path or 'defaults (no config.env found)'}")

    source_kind = args.source or ("file" if args.play else cfg["SOURCE"])
    default_device = None
    try:
        if source_kind == "file":
            path = args.play
            if not path:
                log("ERROR: --source file needs --play FILE")
                return 2
            source = FileSource(path, loop=args.loop, speed=args.speed)
        elif source_kind == "serial":
            source = open_serial_source(
                args.serial_port or cfg["SERIAL_PORT"],
                args.baud or int(cfg["BAUD_RATE"]))
            # A cable carries exactly one sensor, so the wired frames have
            # no DeviceID and the transport is the identity.
            default_device = cfg["SERIAL_DEVICE_ID"]
        else:
            source = UdpSource(cfg["LISTEN_HOST"],
                               args.listen_port or int(cfg["LISTEN_PORT"]))
    except Exception as e:                       # noqa: BLE001
        log(f"ERROR opening the {source_kind} source: {e}")
        return 1
    log(f"source: {source.describe()}")

    engine = Engine(cfg, log=log)
    try:
        server = Server(cfg["CONTROL_HOST"],
                        args.control_port or int(cfg["CONTROL_PORT"]),
                        engine, ttl=float(cfg["SUBSCRIPTION_TTL"]), log=log)
    except Exception as e:                       # noqa: BLE001
        log(f"ERROR opening the control socket: {e}")
        source.close()
        return 1
    log(f"consumers: {server.describe()}")

    recorder = None
    if args.record:
        recorder = Recorder(args.record, note=f"veleta core {__version__}")
        log(f"recording to {args.record}")

    calib_deadline = None
    if cfg["AUTO_CALIBRATE"] == "1":
        calib_deadline = time.time() + float(cfg["CALIB_COUNTDOWN"])
        log(f"auto-calibration in {float(cfg['CALIB_COUNTDOWN']):.0f}s: put "
            f"the sensor(s) in the reference pose")

    stop_at = (time.time() + args.duration) if args.duration else None
    log("running. Ctrl-C to stop.")
    try:
        while True:
            now = time.time()
            if stop_at and now >= stop_at:
                break
            if calib_deadline is not None and now >= calib_deadline:
                calib_deadline = None
                engine.calibrate()

            server.poll()
            batch = source.poll()
            for line, t in batch:
                if recorder is not None:
                    recorder.write(line, t)
                pose = engine.feed(line, now=t, default_device=default_device)
                if pose is not None:
                    server.broadcast(pose)

            if getattr(source, "exhausted", False):
                log("recording finished")
                break
            if not batch:
                time.sleep(0.001)   # idle: do not spin a core at 100%
    except KeyboardInterrupt:
        log("stopping")
    finally:
        if recorder is not None:
            recorder.close()
            log(f"recorded {recorder.count} frames to {args.record}")
        server.close()
        source.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
