#!/usr/bin/env python3
"""Build one v3 episode end to end: 8 hours, a title card that dissolves into black, one file.

    python3 build_episode.py 6 --out-dir /home/claude/out/ep006

This is the ONLY build command for the sleep channel. It replaces render_scene.py + make_extras.py,
which built the v2 three-upload pack. It exists because every step below has a trap in it that cost
us an hour each when they were discovered by hand on ep005 (18 Nov):

  - WAV cannot hold 8 h of audio (32-bit sizes, 4 GiB ceiling), so audio goes to raw PCM.
  - A Piece is a function of absolute time apart from its reverb tail, so the audio renders as two
    halves in parallel on two cores: ~28 min instead of ~55.
  - The `night` mood lands ~8 dB quieter than `rain`, and YouTube never raises quiet audio. The gain
    is therefore measured, not guessed, and a limiter catches the bell peaks.
  - x264 spends ~84 bytes on every black frame, so an 8 h black video is ~59 MB and the audio has to
    fit in what is left under the 400 MB delivery limit.

Everything it produces is checked before it returns: duration, audio presence, loudness, file size,
and that the picture really is black after the card.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

SR = 44100
CTA_IN = 13.0                # seconds: when the subscribe line appears on the card
TARGET_LUFS = -18.5          # what ep001-004 measured; YouTube turns loud down but never quiet up
LIMIT_BYTES = 400 * 1024 ** 2   # SendUserFile's ceiling. The device bridge is stricter (400 MB
                                # decimal), so FPS below keeps a real file near 370 MB and under both.
AAC_BITRATE = "92k"          # 96k would push an 8 h file past the cap once the black video is added

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "shared"))


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)


def ff(args):
    sh(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"] + args)


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return out.strip().split(",")


def measure_lufs(path, extra_in=(), ss=3600, dur=300, total=None):
    """Integrated loudness of a 5-minute window. Five minutes, not ten seconds: short windows on
    sparse ambient read several dB low and would lead to over-correcting the gain."""
    if total:                      # keep the window inside the file (matters for short test renders)
        ss = min(ss, max(0, total * 0.25))
        dur = min(dur, max(5, total - ss))
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-ss", str(ss), "-t", str(dur)]
    cmd += list(extra_in) + ["-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.findall(r"I:\s*(-?\d+\.\d+) LUFS", err)
    p = re.findall(r"Peak:\s*(-?\d+\.\d+) dBFS", err)
    return (float(m[-1]) if m else None), (float(p[-1]) if p else None)


def render_audio(d, out_dir, log):
    """Two halves at once. See the module docstring for why this is safe."""
    import ambient
    dur = int(d["hours"] * 3600)
    half = int(dur // 2)
    segs = [os.path.join(out_dir, f"seg{i}.pcm") for i in range(2)]
    procs = []
    for i, (t0, t1) in enumerate(((0, half), (half, dur))):
        code = (f"import sys; sys.path.insert(0, {os.path.join(os.path.dirname(HERE), 'shared')!r});"
                f"import ambient; ambient.render_pcm({segs[i]!r}, {dur}, seed={d['seed']},"
                f" key={d['key']}, mood={d['mood']!r}, t0={t0}, t1={t1})")
        procs.append(subprocess.Popen([sys.executable, "-c", code],
                                      stdout=open(os.path.join(out_dir, f"seg{i}.log"), "w"),
                                      stderr=subprocess.STDOUT))
    log(f"  rendering {d['hours']} h of audio as two halves on two cores")
    while any(p.poll() is None for p in procs):
        time.sleep(20)
    for i, p in enumerate(procs):
        if p.returncode != 0:
            raise SystemExit(f"audio half {i} failed; see seg{i}.log")

    pcm = os.path.join(out_dir, "audio.pcm")
    with open(pcm, "wb") as w:
        for s in segs:
            with open(s, "rb") as r:
                shutil.copyfileobj(r, w, 1 << 24)
    want = int(dur) * SR * 4
    got = os.path.getsize(pcm)
    if got != want:
        raise SystemExit(f"audio is {got} bytes, expected {want}")
    for s in segs:
        os.remove(s)
    log(f"  audio ok: {got / 1e9:.2f} GB, {got / (SR * 4):.0f} s")
    return pcm


def build_video(d, out_dir, log):
    """Title card for `intro` seconds, dissolving to black over the last 5, then black to the end."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import render_scene as RS

    # 15, not 24: the picture is a title card and then black, and x264 spends ~84 bytes on every
    # black frame whatever is in it. At 24 fps an 8 h black video is 59 MB and the file lands at
    # 406 MB; at 15 fps it is ~37 MB and the file lands near 370 MB, inside both delivery limits.
    # A slow drifting sky loses nothing at 15 fps.
    fps, intro = 15, d["intro"]
    scene = RS.SCENES[d["scene"]](d["seed"], 180)
    frames = os.path.join(out_dir, "frames")
    os.makedirs(frames, exist_ok=True)

    def F(sz, w):
        return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", sz)

    sub = f"{d['hours']:g} Hours · Original Ambient · Black Screen"
    cta = "Subscribe for new episodes"
    # The card is the only moment anyone is looking at the screen, so the ask goes here, late enough
    # that the title has landed and early enough to be gone well before anyone is trying to sleep.
    n = int(intro * fps)
    for i in range(n):
        t = i / fps
        im = Image.fromarray(scene.frame(t)).convert("RGB")
        dr = ImageDraw.Draw(im, "RGBA")
        dr.rectangle([0, 0, RS.W, RS.H], fill=(3, 5, 14, 90))
        f1, f2, f3 = F(96, "Bold"), F(40, "Medium"), F(34, "SemiBold")
        a = min(1.0, max(0.0, (t - 0.8) / 1.5))
        tw = dr.textlength(d["short_title"], font=f1)
        dr.text((RS.W / 2 - tw / 2, RS.H * 0.42), d["short_title"], font=f1, fill=(246, 243, 232, int(255 * a)))
        sw = dr.textlength(sub, font=f2)
        dr.text((RS.W / 2 - sw / 2, RS.H * 0.42 + 120), sub, font=f2, fill=(196, 202, 226, int(235 * a)))
        ca = min(1.0, max(0.0, (t - CTA_IN) / 1.8))
        if ca > 0:
            cw = dr.textlength(cta, font=f3)
            x, y = RS.W / 2 - cw / 2, RS.H * 0.42 + 215
            dr.rounded_rectangle([x - 34, y - 16, x + cw + 34, y + 58], 38,
                                 fill=(255, 214, 112, int(30 * ca)), outline=(255, 214, 112, int(150 * ca)), width=2)
            dr.text((x, y), cta, font=f3, fill=(255, 221, 140, int(246 * ca)))
        arr = np.asarray(im).astype(np.float32)
        fade = 1.0 if t < intro - 5 else max(0.0, (intro - t) / 5.0) ** 1.4
        Image.fromarray(np.clip(arr * fade, 0, 255).astype(np.uint8)).save(f"{frames}/{i:05d}.png")

    intro_mp4 = os.path.join(out_dir, "intro.mp4")
    black = os.path.join(out_dir, "black60.mp4")
    ff(["-r", str(fps), "-i", f"{frames}/%05d.png", "-c:v", "libx264", "-preset", "slow", "-crf", "26",
        "-pix_fmt", "yuv420p", "-r", str(fps), intro_mp4])
    ff(["-f", "lavfi", "-i", f"color=c=black:s={RS.W}x{RS.H}:r={fps}", "-t", "60", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", black])
    reps = int(d["hours"] * 3600 / 60) + 2
    lst = os.path.join(out_dir, "list.txt")
    with open(lst, "w") as f:
        f.write(f"file {intro_mp4}\n" + f"file {black}\n" * reps)
    vid = os.path.join(out_dir, "video_only.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    shutil.rmtree(frames)
    log(f"  video ok: {os.path.getsize(vid) / 1e6:.0f} MB, card {intro} s then black")
    return vid


def mux(d, vid, pcm, out, log):
    """Measure the loudness, work out the gain, limit the peaks, and check the result landed."""
    pcm_in = ["-f", "s16le", "-ar", str(SR), "-ac", "2"]
    lufs, _ = measure_lufs(pcm, pcm_in, total=d["hours"] * 3600)
    gain = 0.0 if lufs is None else round(TARGET_LUFS - lufs, 1)
    gain = max(-6.0, min(14.0, gain))
    log(f"  audio measured {lufs} LUFS -> {gain:+.1f} dB to reach {TARGET_LUFS}")
    af = f"volume={gain}dB,alimiter=limit=0.891:attack=5:release=60"
    ff(["-i", vid] + pcm_in + ["-i", pcm, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", af, "-c:a", "aac", "-b:a", AAC_BITRATE, "-t", str(int(d["hours"] * 3600)),
        "-movflags", "+faststart", out])
    return gain


def verify(d, out, log):
    import numpy as np
    from PIL import Image
    dur = float(probe(out, "format=duration")[0])
    size = os.path.getsize(out)
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", out], capture_output=True, text=True).stdout.split()
    problems = []
    if abs(dur - int(d["hours"] * 3600)) > 2:
        problems.append(f"duration is {dur:.0f} s, expected {int(d['hours'] * 3600)}")
    if "audio" not in " ".join(kinds):
        problems.append("no audio stream")
    if size > LIMIT_BYTES:
        problems.append(f"{size / 1e6:.0f} MB is over the {LIMIT_BYTES / 1e6:.0f} MB delivery limit")
    lufs, peak = measure_lufs(out, total=dur)
    if lufs is not None and abs(lufs - TARGET_LUFS) > 2.5:
        problems.append(f"loudness {lufs} LUFS, wanted about {TARGET_LUFS}")
    # the screen must really be black once the card is gone
    for t in (int(dur) // 2, max(d["intro"] + 5, int(dur) - 20)):
        p = f"/tmp/chk{t}.png"
        ff(["-ss", str(t), "-i", out, "-frames:v", "1", p])
        mx = int(np.asarray(Image.open(p).convert("L")).max())
        os.remove(p)
        if mx > 2:
            problems.append(f"frame at {t} s is not black (max luma {mx})")
    log(f"  {dur:.0f} s · {size / 1e6:.0f} MB · {lufs} LUFS · peak {peak} dBFS")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", type=int)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--hours", type=float, default=None,
                    help="override the planned length; a small value is how you smoke-test this script")
    a = ap.parse_args()
    import metadata
    import render_scene as RS

    d = metadata.plan(a.episode)
    if a.hours:
        d["hours"] = a.hours
    out_dir = a.out_dir or f"/home/claude/out/ep{a.episode:03d}"
    os.makedirs(out_dir, exist_ok=True)
    json.dump(d, open(os.path.join(out_dir, f"ep{a.episode:03d}.json"), "w"), indent=1)
    log = lambda m: print(m, flush=True)
    log(f"ep{a.episode:03d}: {d['title']}")

    pcm = render_audio(d, out_dir, log)
    vid = build_video(d, out_dir, log)
    name = re.sub(r"[^A-Za-z0-9]+", "_", d["short_title"]).strip("_")
    final = os.path.join(out_dir, f"Driftlight_ep{a.episode:03d}_{name}_{d['hours']:g}h.mp4")
    mux(d, vid, pcm, final, log)

    thumb = os.path.join(out_dir, f"Driftlight_ep{a.episode:03d}_thumbnail.jpg")
    RS.thumbnail(RS.SCENES[d["scene"]](d["seed"], 180), thumb, d["thumb_big"], d["thumb_sub"], d["hours"])

    meta = os.path.join(out_dir, f"ep{a.episode:03d}_metadata.txt")
    open(meta, "w").write(
        f"TITLE\n{d['title']}\n\nDESCRIPTION\n{d['description']}\n\nTAGS\n{', '.join(d['tags'])}\n\n"
        "SETTINGS\nVisibility: Private first, then Public when checks pass\nCategory: Music\n"
        "Made for kids: No\nPaid promotion: No\n"
        "Playlist: Sleep Music — Original Ambient (1–8 h)\n"
        f"Thumbnail: {os.path.basename(thumb)}\n\n"
        f"FORMAT v3\nOne upload. {d['hours']} hours. Title card {d['intro']} s, then black to the end.\n"
        "No Short, no separate black-screen upload, no pin.\n")

    problems = verify(d, final, log)
    for f in ("audio.pcm", "video_only.mp4", "intro.mp4", "black60.mp4", "list.txt"):
        p = os.path.join(out_dir, f)
        if os.path.exists(p):
            os.remove(p)
    if problems:
        log("PROBLEMS: " + "; ".join(problems))
    else:
        log("all checks passed")
    log("deliver: " + " ".join(os.path.basename(x) for x in (final, thumb, meta)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
