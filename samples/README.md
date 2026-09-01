# samples — recordings of the sensor stream

One JSON object per line: `{"t": <seconds from the first frame>, "line":
"<the CSV frame>"}`. Format in
[`docs/protocol.md`](../docs/protocol.md#part-3--recordings-samplesjsonl).

```bash
cd core
python3 -m veleta_core --play ../samples/wt901_desk_wobble.jsonl --loop
python3 -m veleta_core --record ../samples/new.jsonl
```

These hold the **sensor** stream, not the core's output, so replaying one
exercises parsing, fusion and calibration exactly as live hardware would.
That is what lets a single file do three jobs: the fixture the tests run
against, the way to reproduce a fault from a recording a user sent without
their hardware on your desk, and a working setup when the sensor is flat,
broken or in another room.

These are the **core's** recordings, so they are only reachable by someone
who has a core, which means someone who has a kit. The extension ships its
own copy of one recording in `blender/demo/`, for people who installed the
extension and own nothing else. The two are deliberately separate files:
this folder can grow real captures freely, while what goes inside the
extension package is a size and licensing decision.

`tests/test_playback.py` replays **every** file in this folder and requires
it to produce poses, so a recording that goes stale fails the build rather
than the demo.

| File | What it is |
|---|---|
| `wt901_desk_wobble.jsonl` | 171 frames, ~4 s, one `fused` sensor. **Synthetic** — generated with `core/tools/fake_sensor.py`, not captured from real hardware. It predates the bring-up of 2026-08-24; real wired and BLE sensors have run since, so a real capture is now merely undone rather than impossible. Replace it with one. |
