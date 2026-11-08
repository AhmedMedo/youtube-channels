"""Procedural ambient / sleep music. 100% generated, no samples, no rights issues.

Renders in 30-second chunks straight to a stereo 16-bit WAV, so an 8-hour file uses almost no RAM.
Every (seed, key, mood) combination gives a different piece: chord order, bell melody, LFO speeds,
rain level and stereo image all derive from the seed.

    python ambient.py out/sleep.wav 3600 --seed 7 --mood night
"""
from __future__ import annotations

import argparse
import math
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, lfilter_zi

SR = 44100
CHUNK = 30  # seconds


def note_hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


# ----------------------------------------------------------------------------- musical material
# Chord voicings in D (transposed by `key`). Low root + open fifth + colour tones; no 3rds in the bass.
CHORDS = {
    "night": [[38, 45, 57, 62, 66, 69], [35, 42, 54, 59, 62, 66], [31, 43, 55, 59, 62, 66], [33, 45, 52, 59, 64, 67]],  # D Bm G A(add9)
    "rain": [[38, 45, 57, 60, 64, 69], [41, 48, 57, 60, 64, 67], [36, 43, 55, 60, 64, 67], [43, 50, 57, 60, 62, 65]],   # Dm F C Gm (minor, cosier)
    "ocean": [[38, 45, 54, 57, 61, 64], [43, 50, 54, 57, 62, 66], [36, 43, 52, 55, 59, 64], [45, 52, 57, 61, 64, 69]],  # D G/D C A
}
BELL_SCALES = {
    "night": [74, 76, 78, 81, 83, 86, 88, 90],  # D major pentatonic
    "rain": [72, 74, 77, 79, 81, 84, 86, 89],   # D minor pentatonic-ish
    "ocean": [73, 76, 78, 81, 85, 88, 90, 93],
}


class Piece:
    def __init__(self, duration, seed=1, key=0, mood="night", rain=None):
        self.dur = float(duration)
        self.rng = np.random.default_rng(seed)
        self.key = key
        self.mood = mood
        rng = self.rng
        self.chord_len = float(rng.uniform(40, 64))     # seconds per chord
        self.xfade = self.chord_len * 0.35
        order = list(range(4))
        rng.shuffle(order)
        self.chords = [CHORDS[mood][i] for i in order]
        self.voice_lfo = [(rng.uniform(13, 37), rng.uniform(0, 2 * math.pi)) for _ in range(6)]
        self.detune = rng.uniform(0.0025, 0.0045)
        # bells: sparse, denser at the start, thinning out as the listener falls asleep
        self.bells = []
        t = rng.uniform(8, 20)
        scale = BELL_SCALES[mood]
        last = None
        while t < self.dur - 30:
            progress = t / self.dur
            m = int(rng.choice(scale))
            if m == last:
                m = int(rng.choice(scale))
            last = m
            self.bells.append((t, m + key, rng.uniform(-0.7, 0.7), rng.uniform(0.5, 1.0) * (1 - 0.4 * progress)))
            gap = rng.uniform(7, 16) * (1 + 1.5 * progress)
            # sometimes a small 2–3 note phrase
            if rng.random() < 0.3:
                for k in range(int(rng.integers(1, 3))):
                    t2 = t + 1.6 * (k + 1) * rng.uniform(0.8, 1.25)
                    self.bells.append((t2, int(rng.choice(scale)) + key, rng.uniform(-0.7, 0.7), rng.uniform(0.35, 0.7)))
            t += gap
        self.rain_level = {"night": 0.12, "rain": 0.55, "ocean": 0.0}[mood] if rain is None else rain
        self.swell_period = rng.uniform(9, 14)  # ocean swell / wind gust period
        # reverb impulse responses (decorrelated L/R)
        self.ir = [self._ir(2.8, s) for s in (1, 2)]
        self.tail = np.zeros((2, len(self.ir[0]) - 1))
        # noise filter states
        self._zi = None

    def _ir(self, T, s):
        rng = np.random.default_rng(1000 + s + int(self.rng.integers(0, 1000)))
        n = int(T * SR)
        t = np.arange(n) / SR
        h = rng.standard_normal(n) * np.exp(-t * (6.9 / T))
        b, a = butter(2, 3200 / (SR / 2))
        h = lfilter(b, a, h)
        h[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        return (h / np.sqrt(np.sum(h ** 2))).astype(np.float32)

    # ------------------------------------------------------------------ layers
    def pads(self, t, side):
        out = np.zeros_like(t)
        L, X = self.chord_len, self.xfade
        n_ch = len(self.chords)
        first = int(np.floor((t[0] - X) / L))
        last = int(np.floor((t[-1] + X) / L))
        sgn = 1 if side == 0 else -1
        for ci in range(max(0, first), last + 1):
            start, end = ci * L, (ci + 1) * L
            env = smoothstep((t - (start - X / 2)) / X) * (1 - smoothstep((t - (end - X / 2)) / X))
            if not env.any():
                continue
            chord = self.chords[ci % n_ch]
            seg = np.zeros_like(t)
            for vi, m in enumerate(chord):
                f = note_hz(m + self.key)
                per, ph = self.voice_lfo[vi % len(self.voice_lfo)]
                lfo = 1 + 0.22 * np.sin(2 * np.pi * t / per + ph + 0.4 * sgn)
                amp = 1.0 if vi > 1 else 0.7  # bass voices a bit softer
                for d, g in ((-self.detune * sgn, 0.5), (0, 0.6), (self.detune * sgn, 0.5)):
                    seg += g * np.sin(2 * np.pi * f * (1 + d) * t + ph * (vi + 1))
                seg += 0.18 * np.sin(2 * np.pi * 2 * f * t + ph)        # soft 2nd harmonic
                seg += 0.05 * np.sin(2 * np.pi * 3 * f * t + 2 * ph)    # tiny 3rd
                seg *= 1  # keep
                out += seg * env * lfo * amp / len(chord)
                seg[:] = 0
        return out * 0.11

    def bell_layer(self, t):
        outL = np.zeros_like(t)
        outR = np.zeros_like(t)
        t0, t1 = t[0], t[-1]
        for (bt, m, pan, vel) in self.bells:
            if bt > t1 or bt + 7 < t0:
                continue
            tt = t - bt
            msk = tt >= 0
            if not msk.any():
                continue
            tt = tt[msk]
            f = note_hz(m)
            y = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 1.1)
                 + 0.35 * np.sin(2 * np.pi * 2.0 * f * tt) * np.exp(-tt * 2.6)
                 + 0.12 * np.sin(2 * np.pi * 3.01 * f * tt) * np.exp(-tt * 5.0))
            y *= (1 - np.exp(-tt * 180))  # 5 ms attack
            y *= vel * 0.09
            gl, gr = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            outL[msk] += y * gl
            outR[msk] += y * gr
        return outL, outR

    def noise_bed(self, t):
        """Distant rain / wind: filtered noise with slow swells. Stateful filters keep chunks seamless."""
        n = len(t)
        if self.rain_level <= 0:
            return np.zeros(n), np.zeros(n)
        if self._zi is None:
            self._b1, self._a1 = butter(2, [180 / (SR / 2), 2400 / (SR / 2)], btype="band")
            self._b2, self._a2 = butter(1, 900 / (SR / 2))
            zi1 = lfilter_zi(self._b1, self._a1)
            zi2 = lfilter_zi(self._b2, self._a2)
            self._zi = [[zi1 * 0, zi2 * 0], [zi1 * 0, zi2 * 0]]
        outs = []
        for ch in range(2):
            w = self.rng.standard_normal(n)
            y, self._zi[ch][0] = lfilter(self._b1, self._a1, w, zi=self._zi[ch][0])
            y, self._zi[ch][1] = lfilter(self._b2, self._a2, y, zi=self._zi[ch][1])
            swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / self.swell_period + ch * 1.3) * np.sin(2 * np.pi * t / (self.swell_period * 3.7))
            outs.append(y * swell * 0.045 * self.rain_level)
        return outs[0], outs[1]

    # ------------------------------------------------------------------ render
    def render_chunk(self, start):
        n = int(min(CHUNK, self.dur - start) * SR)
        t = start + np.arange(n) / SR
        padL, padR = self.pads(t, 0), self.pads(t, 1)
        belL, belR = self.bell_layer(t)
        dry = np.stack([padL + belL, padR + belR])
        # reverb (send: bells fully, pads lightly), overlap-add tail across chunks
        send = np.stack([belL * 1.0 + padL * 0.25, belR * 1.0 + padR * 0.25])
        wet = np.stack([fftconvolve(send[c], self.ir[c]) for c in range(2)])
        wet[:, : self.tail.shape[1]] += self.tail
        self.tail = wet[:, n:]
        wet = wet[:, :n]
        nzL, nzR = self.noise_bed(t)
        out = dry + 0.8 * wet + np.stack([nzL, nzR])
        # master fades
        fade = np.minimum(smoothstep(t / 6.0), smoothstep((self.dur - t) / 25.0))
        return (out * fade).astype(np.float32)


def render(path, duration, seed=1, key=0, mood="night", rain=None, gain=1.0, log=print):
    p = Piece(duration, seed=seed, key=key, mood=mood, rain=rain)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        peak = 0.0
        sq = 0.0
        cnt = 0
        start = 0.0
        while start < duration:
            ch = p.render_chunk(start) * gain
            peak = max(peak, float(np.abs(ch).max()))
            sq += float((ch ** 2).sum())
            cnt += ch.size
            pcm = (np.clip(ch.T, -1, 1) * 32767).astype(np.int16)
            w.writeframes(pcm.tobytes())
            start += CHUNK
            if int(start) % 600 == 0:
                log(f"  audio {int(start) // 60} min")
    rms_db = 20 * math.log10(math.sqrt(sq / cnt) + 1e-12)
    log(f"audio done: peak {20 * math.log10(peak + 1e-12):.1f} dBFS, rms {rms_db:.1f} dBFS, bells {len(p.bells)}")
    return peak, rms_db


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("duration", type=float)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--key", type=int, default=0, help="semitone transpose")
    ap.add_argument("--mood", default="night", choices=list(CHORDS))
    ap.add_argument("--rain", type=float, default=None)
    ap.add_argument("--gain", type=float, default=1.0)
    a = ap.parse_args()
    render(a.path, a.duration, a.seed, a.key, a.mood, a.rain, a.gain)
