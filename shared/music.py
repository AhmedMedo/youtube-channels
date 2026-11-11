"""Procedural music v2 — still 100% generated (no samples, no rights issues), but no longer one
four-bar loop on repeat. Three things make it sound less flat than shared/audio.py's `music()`:

  * **structure** — an energy curve over the track (intro, build, full, break, payoff), so parts
    drop in and out instead of every bar being identical;
  * **a real kit** — synthesised kick, snare, hats and an offbeat bass, with sidechain ducking on
    the kick, which is most of what makes a loop feel modern;
  * **variation** — the progression, the key and the arpeggio pattern come from the seed, and a
    fill lands every eighth bar.

    python3 music.py out.wav 25 race 3     # style: race | quiz | chill

API: `track(duration, style="race", seed=0, bpm=None, hits=())`
`hits` are (time_s, kind) markers from the video — "riser", "impact", "drop" — so the music can
follow the picture (riser into the reveal, impact on it).
"""
from __future__ import annotations

import sys

import numpy as np

SR = 44100
ST = {                                  # style -> (bpm, root midi, scale, swing)
    "race": (124, 45, "minor", 0.0),
    "quiz": (104, 48, "minor", 0.04),
    "chill": (82, 46, "dorian", 0.12),
}
SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10], "major": [0, 2, 4, 5, 7, 9, 11]}
PROGS = [[0, 5, 3, 4], [0, 3, 4, 3], [0, 6, 3, 4], [0, 4, 5, 3], [0, 5, 1, 4]]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a, r, sustain=1.0):
    e = np.full(n, sustain)
    a, r = min(n, int(a * SR)), 0 if n == 0 else min(n, int(r * SR))
    if a:
        e[:a] = np.linspace(0, sustain, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _lp(x, alpha):
    """One-pole lowpass, vectorised over time via lfilter-style recursion in numpy chunks."""
    al = np.broadcast_to(np.asarray(alpha, dtype=float), x.shape)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def _add(buf, pos, sig, gain=1.0):
    s = int(pos)
    if s >= len(buf) or s < -len(sig):
        return
    s = max(0, s)
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s] * gain


# ----------------------------------------------------------------------------- voices
def kick(dur=0.42):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 118 * np.exp(-t * 42) + 46
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    click = np.random.default_rng(1).standard_normal(int(0.004 * SR))
    out = body
    out[: len(click)] += click * 0.25
    return out * 0.95


def snare(dur=0.3, seed=2):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    nz = rng.standard_normal(n)
    nz = nz - _lp(nz, 0.25)                       # keep the top end
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 26) * 0.35
    return (nz * np.exp(-t * 19) + tone) * 0.55


def hat(dur=0.055, seed=3, open_=False):
    n = int((0.26 if open_ else dur) * SR)
    rng = np.random.default_rng(seed)
    nz = rng.standard_normal(n)
    nz = nz - _lp(nz, 0.55)
    t = np.arange(n) / SR
    return nz * np.exp(-t * (9 if open_ else 55)) * 0.3


def tick(dur=0.07, m=84):
    """Clock tick for the quiz style."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * hz(m) * t) + 0.4 * np.sin(2 * np.pi * hz(m + 19) * t)) * np.exp(-t * 60) * 0.5


def bass(m, dur, cut=0.16):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    saw = 2 * ((t * f) % 1.0) - 1.0
    sub = np.sin(2 * np.pi * f * t)
    y = _lp(saw, cut) * 0.7 + sub * 0.6
    return y * _env(n, 0.005, min(0.12, dur * 0.5)) * 0.5


def pluck(m, dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)
    return y * np.exp(-t * 7) * 0.32


def pad(notes, dur, bright=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for m in notes:
        for det in (-0.09, 0.0, 0.09):
            f = hz(m + det / 6)
            y += 2 * ((t * f) % 1.0) - 1.0
    y /= len(notes) * 3
    cut = 0.012 + 0.09 * bright
    return _lp(y, cut) * _env(n, 0.35, 0.5) * 0.42


def riser(dur=1.6, seed=5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = t / dur
    rng = np.random.default_rng(seed)
    nz = _lp(rng.standard_normal(n), 0.02 + 0.5 * k ** 2)
    swp = np.sin(2 * np.pi * np.cumsum(220 + 1500 * k ** 2) / SR) * 0.25
    return (nz * 0.9 + swp) * (k ** 1.6) * 0.5


def impact(dur=1.4, seed=6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    boom = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 9) + 38) / SR) * np.exp(-t * 3.2)
    nz = _lp(rng.standard_normal(n), 0.1) * np.exp(-t * 7)
    return (boom + nz * 0.5) * 0.85


# ----------------------------------------------------------------------------- arrangement
def energy_curve(duration, style, hits):
    """0..1 over time: how full the arrangement is. Rises through the track, dips before a riser."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    if style == "chill":
        e = np.clip(0.45 + 0.25 * t / max(duration, 1), 0, 1)
    else:
        e = np.clip(0.3 + 0.75 * (t / max(duration, 1)) ** 0.75, 0, 1)
    for ht, kind in hits:
        if kind in ("riser", "drop"):            # clear space just before the moment
            m = (t > ht - 1.8) & (t < ht)
            e[m] *= np.linspace(1.0, 0.15, m.sum())
        if kind in ("impact", "drop"):
            m = t >= ht
            e[m] = np.minimum(1.0, e[m] + 0.35)
    return e


def track(duration, style="race", seed=0, bpm=None, hits=()):
    rng = np.random.default_rng(seed)
    base_bpm, root, scale_name, swing = ST.get(style, ST["race"])
    bpm = bpm or base_bpm + int(rng.integers(-4, 5))
    scale = SCALES[scale_name]
    prog = PROGS[int(rng.integers(0, len(PROGS)))]
    n = int(duration * SR)
    beat, bar = 60 / bpm, 4 * 60 / bpm
    drums = np.zeros(n)
    rest = np.zeros(n)
    nbars = int(duration / bar) + 1
    e = energy_curve(duration, style, hits)

    def deg(d, octv=0):
        return root + 12 * octv + scale[d % 7] + 12 * (d // 7)

    pat = [int(x) for x in rng.integers(0, 3, 8)]
    for b in range(nbars):
        t0 = b * bar
        if t0 >= duration:
            break
        lvl = float(e[min(n - 1, int(t0 * SR))])
        ch_d = prog[b % 4]
        notes = [deg(ch_d, 1), deg(ch_d + 2, 1), deg(ch_d + 4, 1)]
        _add(rest, t0 * SR, pad(notes, bar * 1.05, bright=0.25 + 0.6 * lvl), 0.5 + 0.5 * lvl)
        fill = (b % 8 == 7) and style != "chill"
        for k in range(8):                                    # eighth-note grid
            tk = t0 + k * beat / 2 + (swing * beat / 2 if k % 2 else 0)
            if tk >= duration:
                break
            p = tk * SR
            if style == "quiz":
                if lvl > 0.25:
                    _add(drums, p, tick(m=84 + (3 if k % 4 == 0 else 0)), 0.5 + 0.5 * lvl)
                if k == 0 and lvl > 0.45:
                    _add(drums, p, kick(), 0.8)
                if k == 4 and lvl > 0.6:
                    _add(drums, p, snare(), 0.55 * lvl)
            else:
                if k in (0, 3, 6) if style == "race" else (k == 0):
                    _add(drums, p, kick(), 0.85 if lvl > 0.35 else 0.5)
                if k == 4 and lvl > 0.4:
                    _add(drums, p, snare(), 0.5 + 0.5 * lvl)
                if lvl > 0.3:
                    _add(drums, p, hat(open_=(k == 6 and lvl > 0.7)), (0.35 + 0.5 * lvl) * (1.0 if k % 2 == 0 else 0.6))
            if lvl > 0.35 and k % 2 == 0:                      # offbeat-ish bass
                _add(rest, p, bass(deg(ch_d, -1), beat * 0.45), 0.6 + 0.6 * lvl)
            if lvl > 0.5:                                       # arpeggio
                _add(rest, p, pluck(notes[pat[k % 8] % 3] + 12), (0.35 + 0.5 * lvl) * (1.0 if k % 2 == 0 else 0.7))
        if fill:
            for j in range(4):
                _add(drums, (t0 + bar - beat + j * beat / 4) * SR, snare(0.18, seed=10 + j), 0.3 + 0.12 * j)

    for ht, kind in hits:                                       # picture-driven moments
        if kind in ("riser", "drop"):
            _add(rest, (ht - 1.6) * SR, riser(1.6), 0.9)
        if kind in ("impact", "drop"):
            _add(drums, ht * SR, impact(), 0.9)

    duck = np.ones(n)                                           # sidechain: duck everything on the kick
    kb = beat / 2
    for k in range(int(duration / kb) + 1):
        p = int(k * kb * SR)
        if p >= n:
            break
        seg = min(n - p, int(0.26 * SR))
        if (k % 8) in ((0, 3, 6) if style == "race" else (0, 4)):
            duck[p:p + seg] = np.minimum(duck[p:p + seg], np.linspace(0.42, 1.0, seg))
    out = drums + rest * duck
    out *= _env(n, 0.8, 1.6)
    peak = np.abs(out).max() + 1e-9
    return out / peak * 0.85


def write_wav(path, mono):
    import wave
    st = np.stack([mono, mono], axis=1)
    d = np.clip(st, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((d * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "preview.wav"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    sty = sys.argv[3] if len(sys.argv) > 3 else "race"
    sd = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    write_wav(out, track(dur, sty, sd, hits=[(dur - 5.5, "drop")]))
    print("->", out, sty, dur, "s")
