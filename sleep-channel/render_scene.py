"""Sleep channel — slow original visual scenes + procedural music → long MP4.

Strategy: render ONE seamless loop (default 180 s) frame by frame with numpy, encode it once, then
stream-copy it N times with ffmpeg and mux the full-length music. A 1–8 hour video therefore costs
~5 minutes of rendering, and no two videos share a scene (seed drives stars, moon, mountains, fog).

    python render_scene.py --scene night_sky --seed 7 --duration 3600 --out out/video.mp4
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))
import ambient  # noqa: E402

W, H = 1920, 1080
FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(size, weight="Bold"):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Inter-{weight}.otf"), size)


def periodic_noise(rng, w, h, cells_x, cells_y, octaves=3):
    """Smooth noise that tiles seamlessly in x (and y). Built from upsampled random grids."""
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    for o in range(octaves):
        cx, cy = cells_x * 2 ** o, cells_y * 2 ** o
        g = rng.random((cy, cx)).astype(np.float32)
        g3 = np.tile(g, (3, 3))
        img = Image.fromarray((g3 * 255).astype(np.uint8)).resize((w * 3, h * 3), Image.BICUBIC)
        a = np.asarray(img, np.float32) / 255.0
        out += amp * a[h: 2 * h, w: 2 * w]
        amp *= 0.5
    out -= out.min()
    out /= out.max() + 1e-6
    return out


def gaussian_blob(layer, x, y, r, b):
    """Add a soft star at (x, y) wrapping around in x."""
    h, w = layer.shape
    R = int(math.ceil(3 * r))
    xs = np.arange(-R, R + 1)
    g = np.exp(-(xs[None, :] ** 2 + xs[:, None] ** 2) / (2 * r * r)) * b
    yi, xi = int(round(y)), int(round(x))
    y0, y1 = max(0, yi - R), min(h, yi + R + 1)
    if y1 <= y0:
        return
    gy = g[y0 - (yi - R): y1 - (yi - R)]
    for xo in (xi - R, xi - R + w, xi - R - w):
        if xo + 2 * R + 1 <= 0 or xo >= w:
            continue
        x0, x1 = max(0, xo), min(w, xo + 2 * R + 1)
        layer[y0:y1, x0:x1] += gy[:, x0 - xo: x1 - xo]


class NightSky:
    """Stars drifting slowly past a moon above dark mountains, with ground fog. Seamless in `loop` s."""

    def __init__(self, seed, loop):
        self.loop = loop
        rng = np.random.default_rng(seed)
        self.rng = rng
        # --- sky gradient (vertical) with a warm tint near the horizon
        top = np.array(rng.uniform([4, 6, 18], [10, 12, 32]), np.float32)
        hor = np.array(rng.uniform([30, 24, 60], [52, 36, 90]), np.float32)
        ty = (np.arange(H, dtype=np.float32) / H)[:, None, None] ** 1.6
        self.sky = top * (1 - ty) + hor * ty  # H x 1 x 3
        self.sky = np.broadcast_to(self.sky, (H, W, 3)).copy()
        # --- milky way: a tilted soft band of periodic noise
        mw = periodic_noise(rng, W, H, 6, 4, 4)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # band centre follows a gentle sine wave across x → periodic in x, so the drift has no seam
        cy = rng.uniform(0.25, 0.5) * H
        wave_a, wave_ph = rng.uniform(0.06, 0.16) * H, rng.uniform(0, 2 * math.pi)
        centre = cy + wave_a * np.sin(2 * np.pi * xx / W + wave_ph)
        band = np.exp(-((yy - centre) ** 2) / (2 * (H * 0.11) ** 2))
        self.milky = (mw ** 2.2 * band * rng.uniform(0.35, 0.6)).astype(np.float32)
        mcol = np.array(rng.uniform([120, 110, 170], [170, 150, 220]), np.float32)
        self.milky_rgb = self.milky[:, :, None] * mcol[None, None, :]
        # --- stars in twinkle groups (periodic over the loop)
        self.groups = []
        n_groups = 6
        layers = [np.zeros((H, W), np.float32) for _ in range(n_groups)]
        cols = [np.zeros((H, W, 3), np.float32) for _ in range(n_groups)]
        n_stars = int(rng.integers(1400, 2000))
        for i in range(n_stars):
            x, y = rng.uniform(0, W), rng.uniform(0, H * 0.78) ** 1.0
            mag = rng.random()
            r = 0.9 + 2.3 * mag ** 6
            b = 0.25 + 0.75 * mag ** 3
            tint = rng.choice([(1.0, 1.0, 1.0), (0.85, 0.9, 1.0), (1.0, 0.92, 0.8), (0.95, 0.95, 1.0)], p=[0.5, 0.25, 0.15, 0.10])
            g = int(rng.integers(0, n_groups))
            gaussian_blob(layers[g], x, y, r, b)
            for c in range(3):
                gaussian_blob(cols[g][:, :, c], x, y, r, b * tint[c])
        self.star_layers = cols
        del layers
        # twinkle: integer number of cycles per loop → seamless
        self.twinkle = [(int(rng.integers(19, 61)), rng.uniform(0, 2 * math.pi), rng.uniform(0.25, 0.45)) for _ in range(n_groups)]
        self.drift_px = W  # exactly one wrap per loop
        # --- moon
        self.moon_x = rng.uniform(0.62, 0.82) * W
        self.moon_y = rng.uniform(0.18, 0.32) * H
        self.moon_r = rng.uniform(48, 80)
        self.moon_phase = rng.uniform(0.35, 1.0)  # 1 = full
        self.moon_rgb = self._moon()
        # --- mountains + pines (static foreground), with a glow layer
        self.fg_mask, self.fg_rgb = self._foreground(rng)
        # --- fog (periodic noise, drifts the other way, 1 wrap per loop)
        fog = periodic_noise(rng, W, 320, 5, 2, 3)
        fy = np.linspace(0, 1, 320, dtype=np.float32)[:, None]
        fog = fog * (fy ** 1.5) * rng.uniform(0.25, 0.45)
        self.fog = fog.astype(np.float32)
        self.fog_y0 = int(H * 0.62)
        self.fog_col = np.array([70, 70, 105], np.float32)
        # --- shooting star: one per loop
        self.shoot_t = rng.uniform(loop * 0.1, loop * 0.9)
        sx = rng.uniform(0.15, 0.6) * W
        sy = rng.uniform(0.08, 0.3) * H
        self.shoot = (sx, sy, sx + rng.uniform(240, 420), sy + rng.uniform(90, 170))
        # --- parallax cloud wisps (two periodic layers, 1 and 2 wraps per loop)
        self.clouds = []
        for k, (cy0, hh, speed, alpha) in enumerate(((0.05, 260, 1, 0.16), (0.30, 220, 2, 0.11))):
            cn = periodic_noise(rng, W, hh, 7 + k, 2, 3)
            fy = np.sin(np.linspace(0, math.pi, hh, dtype=np.float32))[:, None]
            cn = np.clip((cn - 0.45) * 2.2, 0, 1) * fy * alpha
            self.clouds.append((int(H * cy0), cn.astype(np.float32), speed))
        self.cloud_col = np.array([150, 150, 200], np.float32)
        # --- lake: everything below lake_y is a rippling reflection of what is above it
        self.lake_y = int(H * 0.76)
        self.lake_h = H - self.lake_y
        self.lake_col = np.array([10, 12, 34], np.float32)
        ry = np.arange(self.lake_h, dtype=np.float32)
        self.ripple_phase = (2 * np.pi * ry / rng.uniform(9, 14))[:, None]
        self.ripple_k = int(rng.integers(12, 20))  # ripple cycles per loop
        self.ripple_amp = (2.0 + 6.0 * ry / self.lake_h)[:, None]
        self.lake_fade = (0.55 - 0.35 * (ry / self.lake_h) ** 0.8)[:, None, None].astype(np.float32)
        self.xidx = np.arange(W)[None, :]
        # moonlight path on the water: a soft vertical streak under the moon, widening towards the viewer
        lx = np.arange(W, dtype=np.float32)[None, :]
        width = (40 + 120 * ry / self.lake_h)[:, None]
        streak = np.exp(-((lx - self.moon_x) ** 2) / (2 * width ** 2)) * (0.35 + 0.25 * ry / self.lake_h)[:, None]
        self.moon_path = (streak[:, :, None] * np.array([70, 62, 40], np.float32)).astype(np.float32)
        # --- mascot (Driftlight cloud) asleep top-left, breathing, with floating zzz
        mpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand", "out", "driftlight_character_rgba.png")
        self.mascot = Image.open(mpath).convert("RGBA") if os.path.exists(mpath) else None
        self.mascot_size = 340
        self.mascot_pos = (int(W * 0.06), int(H * 0.10))
        self.breath_k = int(rng.integers(28, 40))  # breaths per loop (≈ 4.5–6.5 s each)
        self.zzz_k = self.breath_k // 2             # one zzz cycle every two breaths
        self.font_z = font(54, "Bold")
        # --- vignette
        vx = (np.arange(W, dtype=np.float32) - W / 2) / (W / 2)
        vy = (np.arange(H, dtype=np.float32) - H / 2) / (H / 2)
        self.vig = (1 - 0.35 * np.clip(np.sqrt(vx[None, :] ** 2 + vy[:, None] ** 2) - 0.45, 0, 1) ** 1.5)[:, :, None].astype(np.float32)

    def _moon(self):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x, y, r = self.moon_x, self.moon_y, self.moon_r
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([x - r * 2.6, y - r * 2.6, x + r * 2.6, y + r * 2.6], fill=(255, 236, 200, 90))
        glow = glow.filter(ImageFilter.GaussianBlur(r * 1.1))
        ga = np.asarray(glow, np.float32)
        self.moon_glow = (ga[:, :, :3] * ga[:, :, 3:4] / 255.0, ga[:, :, 3:4] / 255.0)
        disc = Image.new("L", (W, H), 0)
        dd = ImageDraw.Draw(disc)
        dd.ellipse([x - r, y - r, x + r, y + r], fill=255)
        if self.moon_phase < 0.97:
            off = r * (1 - self.moon_phase) * 2.2
            dd.ellipse([x - r + off, y - r - 2, x + r + off, y + r + 2], fill=0)
        disc = disc.filter(ImageFilter.GaussianBlur(1.2))
        body = Image.new("RGBA", (W, H), (250, 242, 220, 255))
        img.paste(body, (0, 0), disc)
        a = np.asarray(img, np.float32)
        return a[:, :, :3] * a[:, :, 3:4] / 255.0, a[:, :, 3:4] / 255.0

    def _foreground(self, rng):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        # two mountain ridges
        for ridge, base, amp, col in ((0, 0.60, 0.14, 120), (1, 0.68, 0.08, 255)):
            pts = [(0, H)]
            x = 0
            y = base * H
            while x <= W:
                pts.append((x, y))
                x += rng.uniform(60, 160)
                y = np.clip(y + rng.uniform(-amp, amp) * H * 0.5, (base - amp) * H, (base + amp * 0.3) * H)
            pts.append((W, H))
            d.polygon(pts, fill=col)
        # pines on the near ridge
        arr = np.asarray(m)
        for _ in range(int(rng.integers(18, 34))):
            x = rng.uniform(0, W)
            col = arr[:, int(min(W - 1, x))]
            ys = np.where(col == 255)[0]
            if len(ys) == 0:
                continue
            y = ys[0] + rng.uniform(-6, 14)
            h = rng.uniform(60, 140)
            d.rectangle([x - h * 0.03, y - h * 0.3, x + h * 0.03, y + 10], fill=255)
            for k in range(4):
                w = h * (0.13 + 0.08 * k)
                yy = y - h + k * h * 0.2
                d.polygon([(x, yy), (x - w, yy + h * 0.32), (x + w, yy + h * 0.32)], fill=255)
        a = np.asarray(m, np.float32) / 255.0
        far = (a > 0.3) & (a < 0.9)
        near = a >= 0.9
        rgb = np.zeros((H, W, 3), np.float32)
        rgb[far] = np.array([14, 14, 34], np.float32)
        rgb[near] = np.array([5, 5, 14], np.float32)
        mask = ((a > 0.3).astype(np.float32))[:, :, None]
        # soften edges slightly
        mask = np.asarray(Image.fromarray((mask[:, :, 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)[:, :, None] / 255.0
        return mask, rgb

    def frame(self, t):
        T = self.loop
        # stars with twinkle
        stars = np.zeros((H, W, 3), np.float32)
        for lay, (k, ph, depth) in zip(self.star_layers, self.twinkle):
            tw = 1 - depth + depth * 0.5 * (1 + math.sin(2 * math.pi * k * t / T + ph))
            stars += lay * tw
        sky_layer = stars * 255.0 + self.milky_rgb
        # drift with sub-pixel interpolation (exactly one wrap per loop)
        s = (t / T) * self.drift_px
        i, fpart = int(math.floor(s)), s - math.floor(s)
        a = np.roll(sky_layer, i, axis=1)
        b = np.roll(sky_layer, i + 1, axis=1)
        sky_layer = a * (1 - fpart) + b * fpart
        img = self.sky + sky_layer
        # shooting star
        dt = t - self.shoot_t
        if 0 <= dt < 1.1:
            img += self._shoot(dt)
        # parallax cloud wisps over the stars
        for y0, cn, speed in self.clouds:
            sh = int(((t / T) * W * speed) % W)
            c = np.roll(cn, sh, axis=1)[:, :, None]
            reg = img[y0: y0 + cn.shape[0]]
            img[y0: y0 + cn.shape[0]] = reg * (1 - c) + self.cloud_col * c
        # moon with breathing glow
        grgb, galpha = self.moon_glow
        breathe = 0.85 + 0.15 * math.sin(2 * math.pi * self.breath_k * t / T)
        img = img * (1 - galpha * breathe) + grgb * breathe
        mrgb, malpha = self.moon_rgb
        img = img * (1 - malpha) + mrgb
        # fog (drifts the other way)
        fs = -(t / T) * W * 1.0
        fi = int(math.floor(fs)) % W
        fog = np.roll(self.fog, fi, axis=1)
        fog_full = np.zeros((H, W), np.float32)
        fog_full[self.fog_y0: self.fog_y0 + self.fog.shape[0]] = fog
        # foreground
        img = img * (1 - self.fg_mask) + self.fg_rgb * self.fg_mask
        img = img + fog_full[:, :, None] * self.fog_col[None, None, :] * (0.4 + 0.6 * self.fg_mask)
        # lake: rippling reflection of the band just above the shoreline
        # mirror of the shoreline band + the drifting stars "in the water" + a moonlight path
        src = img[self.lake_y - self.lake_h: self.lake_y][::-1] * 0.6 + sky_layer[: self.lake_h][::-1] * 0.9
        shift = np.rint(self.ripple_amp * np.sin(self.ripple_phase + 2 * np.pi * self.ripple_k * t / T)).astype(np.int32)
        idx = (self.xidx + shift) % W
        refl = np.take_along_axis(src, idx[:, :, None], axis=1)
        shimmer = 0.8 + 0.2 * np.sin(self.ripple_phase * 1.7 + 2 * np.pi * (self.ripple_k + 3) * t / T)
        path = self.moon_path * shimmer[:, :, None] if False else self.moon_path * shimmer[:, :, None]
        img[self.lake_y:] = self.lake_col * (1 - self.lake_fade) + refl * self.lake_fade + path
        # shoreline: thin soft highlight
        img[self.lake_y: self.lake_y + 2] = img[self.lake_y: self.lake_y + 2] * 0.6 + np.array([60, 60, 100], np.float32) * 0.4
        img *= self.vig
        out = np.clip(img, 0, 255).astype(np.uint8)
        if self.mascot is not None:
            out = self._mascot(out, t)
        return out

    def _mascot(self, frame_u8, t):
        T = self.loop
        pil = Image.fromarray(frame_u8)
        # breathing: gentle scale around the bottom-centre
        ph = 2 * math.pi * self.breath_k * t / T
        sc = 1 + 0.035 * math.sin(ph)
        size = int(round(self.mascot_size * sc))
        m = self.mascot.resize((size, size), Image.LANCZOS)
        x0, y0 = self.mascot_pos
        px = x0 + (self.mascot_size - size) // 2
        py = y0 + (self.mascot_size - size)
        pil.alpha_composite(m, (px, py)) if pil.mode == "RGBA" else pil.paste(m, (px, py), m)
        # zzz: three z's rising and fading one after another
        layer = Image.new("RGBA", pil.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cyc = (self.zzz_k * t / T) % 1.0
        for k in range(3):
            u = (cyc - k * 0.22) % 1.0
            if u > 0.7:
                continue
            alpha = int(255 * math.sin(math.pi * u / 0.7))
            zx = x0 + self.mascot_size * 0.80 + k * 26 + u * 40
            zy = y0 + self.mascot_size * 0.28 - k * 28 - u * 70
            sz = 0.6 + 0.4 * (k / 2)
            fnt = self.font_z if k == 2 else font(int(54 * (0.65 + 0.2 * k)), "Bold")
            d.text((zx, zy), "z", font=fnt, fill=(255, 236, 180, alpha))
        pil = Image.alpha_composite(pil.convert("RGBA"), layer).convert("RGB")
        return np.asarray(pil)

    def _shoot(self, dt):
        x0, y0, x1, y1 = self.shoot
        p = min(1.0, dt / 0.8)
        fade = 1.0 if dt < 0.8 else max(0.0, 1 - (dt - 0.8) / 0.3)
        hx, hy = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
        tl = 0.25
        tx, ty = x0 + (x1 - x0) * max(0, p - tl), y0 + (y1 - y0) * max(0, p - tl)
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        d.line([(tx, ty), (hx, hy)], fill=int(220 * fade), width=3)
        d.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=int(255 * fade))
        im = im.filter(ImageFilter.GaussianBlur(1.6))
        a = np.asarray(im, np.float32)[:, :, None] / 255.0
        return a * np.array([255, 245, 225], np.float32)


from scene_rain_window import RainWindow  # noqa: E402

SCENES = {"night_sky": NightSky, "rain_window": RainWindow}


def _fit(d, text, weight, max_w, start):
    size = start
    while size > 40 and d.textlength(text, font=font(size, weight)) > max_w:
        size -= 6
    return font(size, weight)


def thumbnail(scene, path, big, sub, hours=None):
    """Mobile-first thumbnail: scene frame + ONE big keyword, a short sub line and an hours badge (left side)."""
    cozy = isinstance(scene, RainWindow)
    m0 = scene.mascot
    if not cozy:
        scene.mascot = None   # night sky: hide the small mascot, paste a big one on the right
    fr = Image.fromarray(scene.frame(scene.loop * 0.37)).resize((1280, 720), Image.LANCZOS)
    scene.mascot = m0
    if not cozy and m0 is not None:
        m = m0.resize((460, 460), Image.LANCZOS)
        fr.paste(m, (1280 - 480, 150), m)
    d = ImageDraw.Draw(fr, "RGBA")
    ink = (10, 8, 30)
    lines = big.upper().split("|")
    f1 = min((_fit(d, ln, "Black", 560 if cozy else 720, 250 if len(lines) == 1 else 190) for ln in lines), key=lambda f: f.size)
    y = 150 if len(lines) == 1 else 110
    for ln in lines:
        d.text((50, y), ln, font=f1, fill=(255, 243, 214), stroke_width=10, stroke_fill=ink)
        y += int(f1.size * 1.0)
    y += 14
    if sub:
        d.text((58, y), sub, font=font(64, "Bold"), fill=(196, 210, 255), stroke_width=6, stroke_fill=ink)
        y += 104
    if hours:
        label = f"{hours} HOUR" + ("S" if hours > 1 else "")
        fb = font(72, "Black")
        w = d.textlength(label, font=fb)
        d.rounded_rectangle([56, y, 56 + w + 60, y + 108], radius=54, fill=(255, 170, 70))
        d.text((86, y + 12), label, font=fb, fill=(30, 16, 10))
    fr.save(path, quality=93)


def render(args):
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    base = os.path.splitext(args.out)[0]
    wav = base + ".wav"
    seg = base + "_loop.mp4"
    t0 = time.time()
    # 1) music
    if not (args.reuse_audio and os.path.exists(wav)):
        print("rendering music …", flush=True)
        ambient.render(wav, args.duration + 1, seed=args.seed, key=args.key, mood=args.mood, rain=args.rain, gain=args.gain,
                       log=lambda s: print(s, flush=True))
    # 2) scene loop
    print("building scene …", flush=True)
    scene = SCENES[args.scene](args.seed, args.loop)
    thumbnail(scene, base + "_thumb.jpg", args.thumb_big or args.title, args.thumb_sub if args.thumb_big else args.subtitle,
              max(1, round(args.duration / 3600)))
    Image.fromarray(scene.frame(0)).save(base + "_still.png")
    n_frames = int(args.loop * args.fps)
    print(f"rendering loop: {n_frames} frames", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(args.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                           "-g", str(args.fps * 2), "-tune", "stillimage", "-movflags", "+faststart", seg],
                          stdin=subprocess.PIPE)
    for k in range(n_frames):
        ff.stdin.write(scene.frame(k / args.fps).tobytes())
        if k % (args.fps * 30) == 0:
            print(f"  frame {k}/{n_frames}  ({time.time() - t0:.0f}s)", flush=True)
    ff.stdin.close()
    ff.wait()
    # 3) loop + mux
    loops = int(math.ceil(args.duration / args.loop))
    print(f"muxing {loops} loops …", flush=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", str(loops - 1), "-i", seg, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(args.duration), "-movflags", "+faststart", args.out], check=True)
    print(f"done in {time.time() - t0:.0f}s → {args.out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="night_sky", choices=list(SCENES))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--duration", type=float, default=3600)
    ap.add_argument("--loop", type=float, default=180)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--crf", type=int, default=22)
    ap.add_argument("--mood", default="night", choices=list(ambient.CHORDS))
    ap.add_argument("--key", type=int, default=0)
    ap.add_argument("--gain", type=float, default=2.5)
    ap.add_argument("--title", default="Starlight Drift")
    ap.add_argument("--subtitle", default="1 Hour · Original Sleep Music")
    ap.add_argument("--thumb-big", default=None, help="big thumbnail keyword(s); use | for a line break")
    ap.add_argument("--thumb-sub", default="")
    ap.add_argument("--rain", type=float, default=None, help="rain bed level 0..1 (default: by mood)")
    ap.add_argument("--out", default="out/video.mp4")
    ap.add_argument("--reuse-audio", action="store_true")
    render(ap.parse_args())
