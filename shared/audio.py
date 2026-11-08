"""Procedural audio: background music + sound effects. 100% generated, no samples, no rights issues.

Used by render_v2.py; can also be run alone to preview:
    python audio.py out/preview.wav 30
"""
from __future__ import annotations

import sys
import wave

import numpy as np

SR = 44100


def _env(n, attack, release):
    e = np.ones(n)
    a = min(n, int(attack * SR))
    r = min(n - a, int(release * SR))
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _lowpass(x, alpha):
    """One-pole lowpass; alpha may be an array (time-varying)."""
    y = np.empty_like(x)
    acc = 0.0
    al = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def note_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# ----------------------------------------------------------------------------- sfx
def whoosh(dur=0.38, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    sweep = np.linspace(0.02, 0.35, n) ** 1.2          # cutoff opens up
    y = _lowpass(noise, sweep) - _lowpass(noise, sweep * 0.15)  # band-ish
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t) ** 1.5
    return 0.55 * y * env / (np.abs(y).max() + 1e-9)


def pop(dur=0.09):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.linspace(950, 520, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.5 * np.sin(ph) * np.exp(-t * 45)


def ding(dur=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 1318.5 * t) + 0.45 * np.sin(2 * np.pi * 2637 * t)
         + 0.2 * np.sin(2 * np.pi * 3955 * t))
    return 0.35 * y * np.exp(-t * 5.5) * _env(n, 0.003, 0.05)


def bonk(dur=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.linspace(260, 110, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.55 * (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-t * 11)


def fanfare():
    out = np.zeros(int(1.4 * SR))
    for i, m in enumerate([72, 76, 79, 84]):
        s = int(i * 0.11 * SR)
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        y = np.sin(2 * np.pi * note_hz(m) * t) + 0.3 * np.sin(4 * np.pi * note_hz(m) * t)
        y *= np.exp(-t * 4) * 0.28
        out[s:s + n] += y[: len(out) - s]
    return out


SFX = {"whoosh": whoosh, "pop": pop, "ding": ding, "bonk": bonk, "fanfare": fanfare}


# ----------------------------------------------------------------------------- music
def music(duration, bpm=92, seed=1):
    """Light, bouncy loop: pad chords + plucked arpeggio + soft shaker."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    out = np.zeros(n)
    beat = 60 / bpm
    bar = 4 * beat
    # C - G - Am - F  (bright, playful)
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    t_all = np.arange(n) / SR
    # pad
    for bi in range(int(duration / bar) + 1):
        ch = chords[bi % 4]
        s = int(bi * bar * SR)
        L = min(int(bar * SR), n - s)
        if L <= 0:
            break
        t = np.arange(L) / SR
        seg = np.zeros(L)
        for m in ch:
            for det in (-0.12, 0.12):
                seg += np.sin(2 * np.pi * note_hz(m - 12 + det / 10) * t)
        seg *= _env(L, 0.25, 0.35) * 0.035
        out[s:s + L] += seg
    # pluck arpeggio (8th notes)
    step = beat / 2
    pattern = [0, 1, 2, 1, 2, 0, 1, 2]
    for k in range(int(duration / step)):
        ch = chords[int(k * step / bar) % 4]
        m = ch[pattern[k % 8]] + 12
        s = int(k * step * SR)
        L = min(int(0.45 * SR), n - s)
        t = np.arange(L) / SR
        y = (np.sin(2 * np.pi * note_hz(m) * t) + 0.35 * np.sin(4 * np.pi * note_hz(m) * t)
             + 0.12 * np.sin(6 * np.pi * note_hz(m) * t))
        vel = 0.75 + 0.25 * (k % 2 == 0)
        out[s:s + L] += y * np.exp(-t * 9) * 0.06 * vel
    # shaker on off-beats
    for k in range(int(duration / step)):
        if k % 2 == 1:
            s = int(k * step * SR)
            L = min(int(0.06 * SR), n - s)
            nz = rng.standard_normal(L)
            nz = nz - _lowpass(nz, 0.5)  # highpass-ish
            out[s:s + L] += nz * np.exp(-np.arange(L) / SR * 60) * 0.02
    # bass on beat 1 and 3
    for k in range(int(duration / beat)):
        if k % 2 == 0:
            ch = chords[int(k * beat / bar) % 4]
            s = int(k * beat * SR)
            L = min(int(0.5 * SR), n - s)
            t = np.arange(L) / SR
            out[s:s + L] += np.sin(2 * np.pi * note_hz(ch[0] - 24) * t) * np.exp(-t * 5) * 0.09
    # fade in/out
    out *= _env(n, 1.0, 2.0)
    return out


def mix(duration, events, music_gain=0.8):
    """events: list of (time_seconds, sfx_name, gain)."""
    out = music(duration) * music_gain
    cache = {}
    for t0, name, g in events:
        if name not in cache:
            cache[name] = SFX[name]()
        s = int(t0 * SR)
        y = cache[name] * g
        e = min(len(out), s + len(y))
        if s < len(out):
            out[s:e] += y[: e - s]
    peak = np.abs(out).max() + 1e-9
    out = out / peak * 0.89  # ~ -1 dBFS
    return out


def write_wav(path, mono):
    st = np.stack([mono, mono], axis=1)
    pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "out/preview.wav"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 20
    ev = [(2, "whoosh", 1), (2.3, "pop", 1), (5, "ding", 1), (8, "bonk", 1), (dur - 2, "fanfare", 1)]
    write_wav(path, mix(dur, ev))
    print("wrote", path)
