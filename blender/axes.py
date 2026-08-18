"""Axis mapping: from the sensor's frame to the consumer's.

The core stays engine-agnostic and emits orientation in the sensor's own
frame, because Blender is Z-up and Godot is Y-up and no single convention
serves both. Turning that into Blender's axes is this file's job, and it
keeps the rule the project has had from the start:

    A wrong-looking axis is a CONFIGURATION change, never a code change.
    That is what SIGN_* and AXIS_MAP are for.

Nothing here imports `bpy`, so the part that historically got fiddly — the
parsing and the permutation — is testable without Blender.
"""

VALID_SOURCES = ("roll", "pitch", "yaw")
IDENTITY = (("roll", 1.0), ("pitch", 1.0), ("yaw", 1.0))


def parse_axis_map(spec):
    """Turn an AXIS_MAP like "pitch,-roll,yaw" into three (source, sign)
    pairs, for Blender's X, Y and Z.

    Returns (mapping, warning). The mapping falls back to identity when the
    spec is unusable; the warning is what the panel shows the user.

        "roll,pitch,yaw"    -> identity: X=roll, Y=pitch, Z=yaw
        "pitch,roll,yaw"    -> swaps roll and pitch
        "roll,pitch,-yaw"   -> identity but yaw inverted
    """
    tokens = [t.strip().lower() for t in str(spec).split(",")]
    if len(tokens) != 3:
        return list(IDENTITY), (f"AXIS_MAP needs 3 axes, not {len(tokens)} "
                                f"({spec!r}). Using identity.")
    result = []
    for tok in tokens:
        sign = 1.0
        if tok.startswith("-"):
            sign, tok = -1.0, tok[1:].strip()
        elif tok.startswith("+"):
            tok = tok[1:].strip()
        if tok not in VALID_SOURCES:
            return list(IDENTITY), (f"Invalid axis source {tok!r} in "
                                    f"{spec!r}. Using identity.")
        result.append((tok, sign))
    warning = None
    if set(src for src, _ in result) != set(VALID_SOURCES):
        warning = (f"AXIS_MAP does not use roll/pitch/yaw exactly once each "
                   f"({spec!r}). Applied anyway, but it is probably not "
                   f"what you want.")
    return result, warning


def remap(rpy, mapping, signs=(1.0, 1.0, 1.0)):
    """Apply signs and permutation to (roll, pitch, yaw) in degrees.

    Two stages, in this order, and both exist because they fix different
    symptoms: a sign inverts a direction, and no combination of signs can
    swap two axes. "I rotate one axis and ANOTHER one responds" is always
    the permutation.
    """
    roll, pitch, yaw = rpy
    s_roll, s_pitch, s_yaw = signs
    sources = {
        "roll": s_roll * roll,
        "pitch": s_pitch * pitch,
        "yaw": s_yaw * yaw,
    }
    return tuple(sign * sources[src] for src, sign in mapping)
