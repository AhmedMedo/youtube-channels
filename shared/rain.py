"""Procedural rain on a named surface. 100% generated, no samples, no rights issues.

Unlike the thin noise bed in ambient.py, this models rain as what it actually is: thousands of
individual drops hitting a specific surface. Each surface has its own impulse response (a tin roof
rings, glass clicks, canvas thuds, leaves hiss), so "Rain on a Tin Roof" and "Rain on a Canvas Tent"
are audibly different pieces of content, not the same noise renamed.

Layers, per channel:
  1. wash   — the mass of far-off drops, filtered noise with slow swells (stateful, seamless)
  2. drops  — a Poisson impulse train convolved with the surface IR (the character of the surface)
  3. thunder— rare distant rumbles (optional)

Renders in 30-second chunks straight to a stereo 16-bit WAV, so 8 hours uses almost no RAM.

    python rain.py out/rain.wav 3600 --surface tin_roof --seed 7
"""
from __future__ import annotations

import argparse
import math
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, lfilter_zi

SR = 44100
CHUNK = 30

# Each surface gets three tiers of drops, because that is how rain actually reaches an ear:
#   near — the few you hear as individual taps (rate in drops/s, loud)
#   mid  — the many that blur into a patter
#   far  — the wash, synthesised as filtered noise rather than drops
# `res` are the surface's resonances (what makes tin ring and canvas thud), `tone` the lowpass on
# the splash itself, `band`/`wash_lp` shape the wash. Keeping `wash_lp` low is what stops 8 hours
# of rain turning into 8 hours of hiss.
SURFACES = {
    # bright metallic ring, the classic "rain on the shed roof"
    "tin_roof":    dict(near=34, mid=190, dec=0.055, tone=3800,
                        res=[(980, 1.0, 1.0), (1640, 0.75, 1.3), (2850, 0.35, 1.9)],
                        band=(220, 4200), wash_lp=2000, wash=0.05, drop=1.0),
    # sharp little taps on glass with the hollow room behind them
    "window":      dict(near=28, mid=150, dec=0.032, tone=5200,
                        res=[(1850, 1.0, 1.0), (3300, 0.5, 1.6), (5200, 0.18, 2.2)],
                        band=(200, 4600), wash_lp=2400, wash=0.044, drop=0.85),
    # dull damped thud, warm and close — a tent in the rain
    "canvas_tent": dict(near=42, mid=230, dec=0.060, tone=1500,
                        res=[(330, 1.0, 0.8), (620, 0.55, 1.1), (1100, 0.2, 1.6)],
                        band=(110, 1700), wash_lp=900, wash=0.058, drop=1.1),
    # no pitch at all, just a soft broadband patter
    "leaves":      dict(near=55, mid=330, dec=0.030, tone=4600,
                        res=[(760, 0.5, 1.0), (1700, 0.4, 1.5), (3400, 0.2, 2.0)],
                        band=(300, 5000), wash_lp=2600, wash=0.052, drop=0.6),
    # heavy downpour on stone, broad and even
    "mossy_stone": dict(near=46, mid=270, dec=0.038, tone=3200,
                        res=[(540, 0.9, 0.9), (1250, 0.55, 1.3), (2400, 0.25, 1.9)],
                        band=(180, 4000), wash_lp=1800, wash=0.052, drop=0.8),
}


def _drop_ir(rng, spec, size, n_var=6):
    """Single-drop impulse responses for one surface. `size` scales a drop's weight and dullness:
    a near drop is slower and fuller, a mid drop is quicker and thinner."""
    irs = []
    b_tone, a_tone = butter(2, min(spec["tone"] * size, 0.45 * SR) / (SR / 2))
    for _ in range(n_var):
        dec = spec["dec"] * size * rng.uniform(0.75, 1.3)
        n = int(dec * 4 * SR)
        t = np.arange(n) / SR
        splash = lfilter(b_tone, a_tone, rng.standard_normal(n)) * np.exp(-t / (dec * 0.3))
        y = splash * 0.9
        for (f, g, dm) in spec["res"]:                                 # the surface ringing
            f = f * rng.uniform(0.9, 1.12)
            y += g * size * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / (dec / dm))
        y *= 1 - np.exp(-t * 1800)                                     # sub-ms attack, no click
        y /= np.abs(y).max() + 1e-9
        irs.append(y.astype(np.float32))
    return irs


class Rain:
    def __init__(self, duration, seed=1, surface="tin_roof", intensity=1.0, thunder=0.0):
        if surface not in SURFACES:
            raise SystemExit(f"unknown surface {surface!r}; choose from {', '.join(SURFACES)}")
        self.dur = float(duration)
        self.surface = surface
        self.spec = SURFACES[surface]
        self.rng = np.random.default_rng(seed)
        self.intensity = float(intensity)
        self.thunder_rate = float(thunder)          # rumbles per minute
        # two tiers of real drops (near = heard one by one, mid = the patter), own drops per channel
        self.tiers = []
        for name, size, gain, amp in (("near", 1.0, 1.0, 1.6), ("mid", 0.45, 0.30, 0.42)):
            irs = [_drop_ir(self.rng, self.spec, size) for _ in range(2)]
            self.tiers.append((self.spec[name], irs, gain, amp))
        self.ir_n = max(len(i) for (_, irs, _, _) in self.tiers for ch in irs for i in ch)
        self.tail = np.zeros((2, self.ir_n), np.float32)
        self._zi = None
        # the shower breathes: two slow periods that never line up, so no 8-hour pattern
        self.swell_a = self.rng.uniform(95, 160)
        self.swell_b = self.rng.uniform(310, 520)
        self.thunders = []
        if self.thunder_rate > 0:
            tt = 25.0
            while tt < self.dur:
                tt += self.rng.exponential(60.0 / self.thunder_rate)
                if tt < self.dur:
                    self.thunders.append((tt, self.rng.uniform(0.35, 1.0), self.rng.uniform(-0.6, 0.6)))

    def density(self, t):
        """Slow swell in how hard it is raining. Stays within a narrow band: nothing wakes a sleeper."""
        a = np.sin(2 * np.pi * t / self.swell_a)
        b = np.sin(2 * np.pi * t / self.swell_b + 1.1)
        return 0.82 + 0.18 * (0.6 * a + 0.4 * b)

    def wash(self, t):
        """The mass of far-off drops — filtered noise, stateful so chunk joins are inaudible."""
        n = len(t)
        lo, hi = self.spec["band"]
        if self._zi is None:
            self._b1, self._a1 = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band")
            self._b2, self._a2 = butter(3, self.spec["wash_lp"] / (SR / 2))
            z1, z2 = lfilter_zi(self._b1, self._a1), lfilter_zi(self._b2, self._a2)
            self._zi = [[z1 * 0, z2 * 0], [z1 * 0, z2 * 0]]
        d = self.density(t)
        outs = []
        for ch in range(2):
            w = self.rng.standard_normal(n)
            y, self._zi[ch][0] = lfilter(self._b1, self._a1, w, zi=self._zi[ch][0])
            y, self._zi[ch][1] = lfilter(self._b2, self._a2, y, zi=self._zi[ch][1])
            outs.append(y * d * self.spec["wash"] * self.intensity)
        return outs

    def drops(self, t):
        """Poisson impulse trains per channel and tier, convolved with the surface IRs."""
        n = len(t)
        dens = float(self.density(t).mean())
        outs = []
        for ch in range(2):
            acc = np.zeros(n + self.ir_n, np.float32)
            for (base_rate, irs, gain, amp_sc) in self.tiers:
                rate = base_rate * self.intensity * dens
                for ir in irs[ch]:
                    k = self.rng.poisson(rate / len(irs[ch]) * n / SR)
                    tr = np.zeros(n + self.ir_n, np.float32)
                    if k:
                        idx = self.rng.integers(0, n, k)
                        # loudness of a drop: mostly small, a few close/heavy ones
                        amp = self.rng.gamma(2.0, amp_sc, k).astype(np.float32)
                        np.add.at(tr, idx, amp)
                    acc += fftconvolve(tr, ir)[: n + self.ir_n] * gain
            outs.append(acc * self.spec["drop"] * 0.030)
        return outs

    def thunder(self, t):
        """Distant rumble: low filtered noise with a long swelling tail. Never a sharp crack."""
        n = len(t)
        out = [np.zeros(n, np.float32), np.zeros(n, np.float32)]
        for (tt, vel, pan) in self.thunders:
            if tt > t[-1] + 1 or tt + 14 < t[0]:
                continue
            rel = t - tt
            m = (rel >= 0) & (rel < 14)
            if not m.any():
                continue
            r = rel[m]
            env = (1 - np.exp(-r * 1.4)) * np.exp(-r / 3.2)
            w = self.rng.standard_normal(len(r))
            b, a = butter(2, 150 / (SR / 2))
            y = lfilter(b, a, w) * env * vel * 0.32
            y += 0.25 * np.sin(2 * np.pi * self.rng.uniform(28, 46) * r) * env * vel
            gl, gr = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            out[0][m] += y * gl
            out[1][m] += y * gr
        return out

    def render_chunk(self, start):
        n = int(min(CHUNK, self.dur - start) * SR)
        t = start + np.arange(n) / SR
        wl, wr = self.wash(t)
        dl, dr = self.drops(t)
        th = self.thunder(t)
        out = np.zeros((2, n), np.float32)
        for ch, (w, d) in enumerate(((wl, dl), (wr, dr))):
            y = d[:n] + w + th[ch]
            k = min(self.ir_n, n)
            y[:k] += self.tail[ch, :k]          # drops that started in the previous chunk
            out[ch] = y
            over = d[n:]                         # ... and the ones still ringing into the next
            self.tail[ch] = 0
            self.tail[ch, : len(over)] = over
        fade = np.minimum(np.clip(t / 8.0, 0, 1), np.clip((self.dur - t) / 25.0, 0, 1))
        fade = fade * fade * (3 - 2 * fade)
        return (out * fade).astype(np.float32)


def render(path, duration, seed=1, surface="tin_roof", intensity=1.0, thunder=0.0, gain=1.0, log=print):
    p = Rain(duration, seed=seed, surface=surface, intensity=intensity, thunder=thunder)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        peak, sq, cnt, start = 0.0, 0.0, 0, 0.0
        while start < duration:
            ch = p.render_chunk(start) * gain
            peak = max(peak, float(np.abs(ch).max()))
            sq += float((ch.astype(np.float64) ** 2).sum()); cnt += ch.size
            w.writeframes((np.clip(ch, -1, 1).T * 32767).astype("<i2").tobytes())
            start += CHUNK
    rms = 20 * math.log10(math.sqrt(sq / cnt) + 1e-12)
    log(f"rain done: {surface}, peak {20 * math.log10(peak + 1e-12):.1f} dBFS, rms {rms:.1f} dBFS, {len(p.thunders)} rumbles")
    return peak, rms


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("duration", type=float)
    ap.add_argument("--surface", default="tin_roof", choices=sorted(SURFACES))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--intensity", type=float, default=1.0)
    ap.add_argument("--thunder", type=float, default=0.0, help="distant rumbles per minute")
    ap.add_argument("--gain", type=float, default=1.0)
    a = ap.parse_args()
    render(a.path, a.duration, a.seed, a.surface, a.intensity, a.thunder, a.gain)
