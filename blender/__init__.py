"""Veleta — motion sensors driving Blender objects in real time.

WHAT THIS EXTENSION IS, AND IS NOT
    It is a consumer. It connects to the veleta core — a separate program
    that talks to the sensors, fuses their readings and re-exposes the
    result over UDP — and applies what arrives to the scene. It does not
    read sensors, does not open serial ports, and never bundles or ships
    the core: it speaks to it over a documented network protocol.

    That separation is what lets this directory be GPL v3 or later, as the
    Blender extensions platform requires, while the core stays under its
    own terms. See the licence map in the repository README.

WHAT YOU NEED
    The veleta core, running. It comes with the hardware kit. With no core
    running, Connect says so and nothing moves.
"""

import time

import bpy
from bpy.props import (BoolProperty, FloatProperty, IntProperty,
                       StringProperty)
from bpy.types import AddonPreferences, Operator, Panel
from mathutils import Euler, Quaternion

from . import axes, playback
from .client import CoreClient, version_warning

VERSION = "0.1.0"          # kept in step with the core and the firmware

_client = None             # the live CoreClient, or None
_status = "Not connected"  # one line, shown in the panel
_warning = None            # version mismatch or axis-map complaint
_seen = {}                 # DeviceID -> last profile seen
_demo = None               # DemoPlayer while the built-in demo runs

_DEG = 57.29577951308232


# ---------------------------------------------------------------- helpers
def _prefs():
    return bpy.context.preferences.addons[__package__].preferences


def _parse_device_map(raw, default_object):
    """'A:Obj1,B:Obj2,*:Cube' -> {DeviceID: object name}."""
    mapping = {}
    for pair in str(raw).split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        dev, _, obj = pair.partition(":")
        mapping[dev.strip()] = obj.strip()
    if "*" not in mapping:
        mapping["*"] = default_object
    return mapping


def _settings():
    """(mapping, axis_map, signs) from the preferences, re-read each tick so
    the user can retune the axes and see it immediately."""
    prefs = _prefs()
    axis_map, _warn = axes.parse_axis_map(prefs.axis_map)
    return (_parse_device_map(prefs.device_map, prefs.default_object),
            axis_map,
            (prefs.sign_roll, prefs.sign_pitch, prefs.sign_yaw))


def _apply_angles(device, rpy_deg, mapping, axis_map, signs):
    """Put roll/pitch/yaw (degrees, sensor frame) on the mapped object.

    The single place the scene is written, shared by the live stream and by
    the built-in demo — so the demo cannot drift away from the real thing.
    """
    name = mapping.get(device, mapping.get("*", ""))
    obj = bpy.data.objects.get(name)
    if obj is None:
        return False
    mapped = axes.remap(rpy_deg, axis_map, signs)
    e = Euler([v / _DEG for v in mapped], "ZYX")
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = e.to_quaternion()
    return True


def _apply_pose(msg, mapping, axis_map, signs):
    """Put one pose message from the core on its object.

    The core sends orientation in the SENSOR's frame, because it serves
    Blender (Z up) and, later, Godot (Y up), and no single convention
    suits both. Turning it into Blender's axes happens here.
    """
    q = Quaternion(msg["q"])                       # calibrated, sensor frame
    rpy_deg = [v * _DEG for v in q.to_euler("ZYX")]
    return _apply_angles(msg["dev"], rpy_deg, mapping, axis_map, signs)


def _pump():
    """Runs on bpy.app.timers, so the interface never blocks — the one
    rule this project has never broken."""
    global _status
    if _client is None or not _client.connected:
        return None                                 # unregister the timer
    mapping, axis_map, signs = _settings()

    applied = 0
    unassigned = set()
    for msg in _client.poll():
        _seen[msg["dev"]] = msg.get("profile", "?")
        if _apply_pose(msg, mapping, axis_map, signs):
            applied += 1
        else:
            unassigned.add(msg["dev"])
    if unassigned:
        _status = f"No object assigned to: {', '.join(sorted(unassigned))}"
    elif applied:
        _status = f"Receiving: {len(_seen)} sensor(s)"
    return 0.001


def _demo_pump():
    """The built-in demo's timer. Same rule as the live one: never block."""
    global _status, _demo
    if _demo is None:
        return None
    mapping, axis_map, signs = _settings()
    missing = set()
    for device, angles in _demo.due(time.time()):
        if not _apply_angles(device, angles, mapping, axis_map, signs):
            missing.add(device)
    if missing:
        _status = (f"Demo running, but no object is assigned to "
                   f"{', '.join(sorted(missing))}")
    return 0.01


# -------------------------------------------------------------- operators
class VELETA_OT_connect(Operator):
    bl_idname = "veleta.connect"
    bl_label = "Connect"
    bl_description = "Subscribe to the veleta core and start moving objects"

    def execute(self, context):
        global _client, _status, _warning
        if _demo is not None:
            bpy.ops.veleta.demo_stop()
        prefs = _prefs()
        client = CoreClient(prefs.host, prefs.port, prefs.ttl)
        try:
            hello = client.connect()
        except Exception as e:                       # noqa: BLE001
            _client = None
            _status = f"No core at {prefs.host}:{prefs.port} ({e})"
            self.report({"ERROR"}, _status)
            return {"CANCELLED"}
        _client = client
        _warning = version_warning(VERSION, hello)
        _status = f"Connected to core {hello.get('version', '?')}"
        if _warning:
            self.report({"WARNING"}, _warning)
        if not bpy.app.timers.is_registered(_pump):
            bpy.app.timers.register(_pump)
        return {"FINISHED"}


class VELETA_OT_disconnect(Operator):
    bl_idname = "veleta.disconnect"
    bl_label = "Disconnect"
    bl_description = "Stop receiving and drop the subscription"

    def execute(self, context):
        global _client, _status
        if bpy.app.timers.is_registered(_pump):
            bpy.app.timers.unregister(_pump)
        if _client is not None:
            _client.close()
        _client = None
        _seen.clear()
        _status = "Not connected"
        return {"FINISHED"}


class VELETA_OT_calibrate(Operator):
    bl_idname = "veleta.calibrate"
    bl_label = "Calibrate"
    bl_description = ("Take the current orientation of every sensor as its "
                      "zero. Hold the reference pose, then press this")

    def execute(self, context):
        global _status
        if _client is None:
            self.report({"ERROR"}, "Not connected")
            return {"CANCELLED"}
        reply = _client.command("calibrate") or {}
        if reply.get("ok"):
            _status = f"Zeroed {reply.get('calibrated', 0)} sensor(s)"
        else:
            _status = f"Calibration failed: {reply.get('error')}"
            self.report({"ERROR"}, _status)
            return {"CANCELLED"}
        return {"FINISHED"}


class VELETA_OT_recenter(Operator):
    bl_idname = "veleta.recenter"
    bl_label = "Recenter sensor"
    bl_description = ("Re-zero one sensor. This is how you cancel the yaw "
                      "drift of a sensor with no magnetometer")

    device: StringProperty(name="DeviceID", default="")

    def execute(self, context):
        global _status
        if _client is None:
            self.report({"ERROR"}, "Not connected")
            return {"CANCELLED"}
        reply = _client.command("recenter", device=self.device) or {}
        _status = (f"'{self.device}' recentered" if reply.get("ok")
                   else f"Could not recenter '{self.device}'")
        return {"FINISHED"}


class VELETA_OT_demo(Operator):
    bl_idname = "veleta.demo"
    bl_label = "Play demo"
    bl_description = ("Replay the recording bundled with this extension. "
                      "No sensors and no core needed — it shows what the "
                      "product does before you own one")

    def execute(self, context):
        global _demo, _status
        if _demo is not None:                      # pressed again: stop
            return bpy.ops.veleta.demo_stop()
        if _client is not None and _client.connected:
            self.report({"ERROR"},
                        "Disconnect first: the demo and a live sensor would "
                        "fight over the same object")
            return {"CANCELLED"}
        try:
            frames = playback.load_recording()
        except OSError as e:                        # noqa: BLE001
            self.report({"ERROR"}, f"Demo recording unreadable: {e}")
            return {"CANCELLED"}
        if not frames:
            self.report({"ERROR"}, "The bundled demo recording is empty")
            return {"CANCELLED"}
        _demo = playback.DemoPlayer(frames, loop=True)
        _demo.start(time.time())
        _status = f"Demo running ({_demo.length:.0f}s, looping) — no sensors"
        if not bpy.app.timers.is_registered(_demo_pump):
            bpy.app.timers.register(_demo_pump)
        return {"FINISHED"}


class VELETA_OT_demo_stop(Operator):
    bl_idname = "veleta.demo_stop"
    bl_label = "Stop demo"
    bl_description = "Stop the bundled demo"

    def execute(self, context):
        global _demo, _status
        if bpy.app.timers.is_registered(_demo_pump):
            bpy.app.timers.unregister(_demo_pump)
        _demo = None
        _status = "Not connected"
        return {"FINISHED"}


# ------------------------------------------------------------- preferences
class VeletaPreferences(AddonPreferences):
    bl_idname = __package__

    host: StringProperty(
        name="Core host", default="127.0.0.1",
        description="Where the veleta core runs. Normally this machine")
    port: IntProperty(
        name="Core port", default=1400, min=1, max=65535,
        description="The core's control port (CONTROL_PORT in its config.env)")
    ttl: FloatProperty(
        name="Subscription (s)", default=10.0, min=1.0, max=120.0,
        description="How long the core keeps streaming without a renewal")
    device_map: StringProperty(
        name="Sensor -> object", default="*:Cube",
        description="DeviceID:Object pairs, comma separated. '*' is the "
                    "wildcard for sensors not listed")
    default_object: StringProperty(
        name="Default object", default="_UNASSIGNED",
        description="Object for sensors that the map does not name")
    axis_map: StringProperty(
        name="Axis map", default="roll,pitch,yaw",
        description="Which source drives Blender's X,Y,Z. Each is "
                    "roll/pitch/yaw, '-' to invert. Fixes 'I move one axis "
                    "and another one responds'")
    sign_roll: FloatProperty(name="Sign roll", default=1.0)
    sign_pitch: FloatProperty(name="Sign pitch", default=1.0)
    sign_yaw: FloatProperty(name="Sign yaw", default=1.0)
    auto_connect: BoolProperty(
        name="Connect on enable", default=False,
        description="Subscribe as soon as the extension is enabled")

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Core")
        row = col.row(align=True)
        row.prop(self, "host")
        row.prop(self, "port")
        col.prop(self, "ttl")
        col.prop(self, "auto_connect")

        col = layout.column(align=True)
        col.label(text="Scene")
        col.prop(self, "device_map")
        col.prop(self, "default_object")

        col = layout.column(align=True)
        col.label(text="Mounting")
        col.prop(self, "axis_map")
        row = col.row(align=True)
        row.prop(self, "sign_roll", text="Roll")
        row.prop(self, "sign_pitch", text="Pitch")
        row.prop(self, "sign_yaw", text="Yaw")


# --------------------------------------------------------------- interface
class VELETA_PT_panel(Panel):
    bl_label = "Veleta"
    bl_idname = "VELETA_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Veleta"

    def draw(self, context):
        layout = self.layout
        connected = _client is not None and _client.connected

        demo_running = _demo is not None

        row = layout.row(align=True)
        if connected:
            row.operator("veleta.disconnect", icon="UNLINKED")
        else:
            row.operator("veleta.connect", icon="LINKED")
            row.enabled = not demo_running

        if not connected:
            # Somebody who installed the extension without buying a kit has
            # no core to connect to. This is what they can press.
            row = layout.row(align=True)
            if demo_running:
                row.operator("veleta.demo_stop", icon="PAUSE")
            else:
                row.operator("veleta.demo", icon="PLAY")

        box = layout.box()
        box.label(text=_status, icon="INFO")
        if _warning:
            # Old firmware against new software is the commonest fault in a
            # product like this, and it is miserable to diagnose from the
            # symptoms. So it is said here, plainly.
            for line in _warning.split(". "):
                if line.strip():
                    box.label(text=line.strip(), icon="ERROR")

        if connected:
            layout.operator("veleta.calibrate", icon="ORIENTATION_GIMBAL")
            if _seen:
                col = layout.column(align=True)
                col.label(text="Sensors:")
                for dev in sorted(_seen):
                    row = col.row(align=True)
                    row.label(text=f"{dev} [{_seen[dev]}]")
                    op = row.operator("veleta.recenter", text="", icon="LOOP_BACK")
                    op.device = dev


# --------------------------------------------------------------- registration
_classes = (
    VeletaPreferences,
    VELETA_OT_connect,
    VELETA_OT_disconnect,
    VELETA_OT_calibrate,
    VELETA_OT_recenter,
    VELETA_OT_demo,
    VELETA_OT_demo_stop,
    VELETA_PT_panel,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    if _prefs().auto_connect:
        bpy.ops.veleta.connect()


def unregister():
    global _client, _demo
    if bpy.app.timers.is_registered(_pump):
        bpy.app.timers.unregister(_pump)
    if bpy.app.timers.is_registered(_demo_pump):
        bpy.app.timers.unregister(_demo_pump)
    _demo = None
    if _client is not None:
        _client.close()
        _client = None
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
