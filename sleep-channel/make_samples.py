import sys, numpy as np, wave
sys.path.insert(0, "/home/claude/youtube-channels/shared")
import ambient, rain

SR, OUT = 44100, "/home/claude/out/samples/"
DUR = 75.0

def write(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1).T * 32767).astype("<i2").tobytes())

def rain_buf(surface, seed, intensity=1.0, thunder=0.0):
    p = rain.Rain(DUR, seed=seed, surface=surface, intensity=intensity, thunder=thunder)
    parts, s = [], 0.0
    while s < DUR:
        parts.append(p.render_chunk(s)); s += rain.CHUNK
    return np.concatenate(parts, axis=1)

def music_buf(seed, key, mood, bell_until, rain_level=0.0):
    p = ambient.Piece(DUR, seed=seed, key=key, mood=mood, rain=rain_level)
    p.bells = [b for b in p.bells if b[0] < bell_until]      # steadier: bells only at the start
    parts, s = [], 0.0
    while s < DUR:
        parts.append(p.render_chunk(s)); s += ambient.CHUNK
    return np.concatenate(parts, axis=1)

# A — named rain, no music
write(OUT + "A1_tin_roof.wav",    rain_buf("tin_roof", 21))
write(OUT + "A2_window.wav",      rain_buf("window", 34))
write(OUT + "A3_canvas_thunder.wav", rain_buf("canvas_tent", 47, thunder=1.2))
# B — our music, darker and steadier
m = music_buf(seed=1041, key=-5, mood="rain", bell_until=22.0)
write(OUT + "B1_music_dark.wav", m)
# B2 — the same music under soft rain on glass
write(OUT + "B2_music_plus_rain.wav", m * 0.85 + rain_buf("window", 34, intensity=0.55) * 0.9)
print("ok")
