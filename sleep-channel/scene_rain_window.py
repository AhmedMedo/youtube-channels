"""Cozy scene: rainy night seen through a window, fairy lights, candle, the Driftlight cloud asleep on the sill.

Everything is periodic over `loop` seconds (integer cycle counts), so frame(0) == frame(loop).
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
WX0, WY0, WX1, WY1 = 780, 75, 1845, 840     # window glass
FRAME = (62, 42, 44)


def _glow_sprite(r, col):
    s = int(r * 2)
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    g = np.exp(-(((xx - r) ** 2 + (yy - r) ** 2) / (2 * (r / 2.6) ** 2)))
    return g[:, :, None] * np.array(col, np.float32)


class RainWindow:
    def __init__(self, seed, loop):
        self.loop = loop
        rng = np.random.default_rng(seed)
        # ---------- palette varies a little with the seed
        self.wall_top = tuple(int(v) for v in rng.uniform([16, 18, 40], [26, 26, 56]))
        self.wall_bot = tuple(int(v) for v in rng.uniform([26, 20, 38], [36, 28, 50]))
        sky_top = rng.uniform([28, 52, 120], [48, 78, 160])
        sky_bot = rng.uniform([60, 100, 170], [86, 130, 200])
        gw, gh = WX1 - WX0, WY1 - WY0
        self.gw, self.gh = gw, gh
        # ---------- outside (static part): gradient + moon, blurred
        ty = np.linspace(0, 1, gh, dtype=np.float32)[:, None, None]
        out = np.broadcast_to(sky_top * (1 - ty) + sky_bot * ty, (gh, gw, 3)).astype(np.float32).copy()
        mo = Image.new("RGB", (gw, gh), (0, 0, 0))
        md = ImageDraw.Draw(mo)
        mx, my, mr = int(rng.uniform(0.62, 0.86) * gw), int(rng.uniform(0.12, 0.24) * gh), int(rng.uniform(64, 92))
        md.ellipse([mx - mr * 2.4, my - mr * 2.4, mx + mr * 2.4, my + mr * 2.4], fill=(70, 66, 50))
        mo = mo.filter(ImageFilter.GaussianBlur(60))
        ImageDraw.Draw(mo).ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 244, 214))
        mo = mo.filter(ImageFilter.GaussianBlur(2))
        moa = np.asarray(mo, np.float32)
        out = np.maximum(out, moa) + moa * 0.25
        # distant roofs silhouette
        rf = Image.new("L", (gw, gh), 0)
        rd = ImageDraw.Draw(rf)
        x = 0
        while x < gw:
            bw, bh = int(rng.uniform(70, 190)), int(rng.uniform(60, 230))
            rd.rectangle([x, gh - bh, x + bw, gh], fill=255)
            x += bw
        rfa = np.asarray(rf.filter(ImageFilter.GaussianBlur(5)), np.float32)[:, :, None] / 255.0
        out = out * (1 - rfa * 0.55)
        self.outside = out
        # ---------- bokeh city lights in 3 twinkle groups (additive)
        self.bokeh = []
        cols = [(255, 200, 120), (255, 150, 90), (140, 200, 255), (255, 230, 170), (255, 120, 140)]
        for g in range(3):
            im = Image.new("RGB", (gw, gh), (0, 0, 0))
            d = ImageDraw.Draw(im)
            for _ in range(int(rng.integers(9, 14))):
                x, y, r = rng.uniform(0, gw), rng.uniform(gh * 0.5, gh), rng.uniform(20, 62)
                c = cols[int(rng.integers(0, len(cols)))]
                a = rng.uniform(0.35, 0.7)
                d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * a) for v in c))
            self.bokeh.append((np.asarray(im.filter(ImageFilter.GaussianBlur(9)), np.float32),
                               int(rng.integers(5, 14)), rng.uniform(0, 6.28)))
        # ---------- rain streaks (falling) and beads on the glass (sliding slowly)
        n = int(rng.integers(120, 160))
        self.rx = rng.uniform(0, gw, n)
        self.rk = rng.integers(60, 105, n)            # falls per loop
        self.rph = rng.uniform(0, 1, n)
        self.rlen = rng.uniform(26, 84, n)
        self.ra = rng.integers(70, 170, n)
        nb = 46
        self.bx = rng.uniform(10, gw - 10, nb)
        self.bk = rng.integers(1, 4, nb)
        self.bph = rng.uniform(0, 1, nb)
        self.br = rng.uniform(3, 7, nb)
        # ---------- room (static): wall, floor glow, window frame, sill
        room = Image.new("RGB", (W, H), self.wall_top)
        d = ImageDraw.Draw(room)
        for y in range(H):
            t = y / H
            d.line([(0, y), (W, y)], fill=tuple(int(self.wall_top[i] + (self.wall_bot[i] - self.wall_top[i]) * t) for i in range(3)))
        d.rectangle([0, WY1 + 50, W, H], fill=(24, 18, 36))
        gl = Image.new("RGB", (W, H), (0, 0, 0))
        ImageDraw.Draw(gl).ellipse([460, 600, 1460, 1500], fill=(96, 50, 18))
        gl = gl.filter(ImageFilter.GaussianBlur(170))
        room = Image.fromarray(np.clip(np.asarray(room, np.float32) + np.asarray(gl, np.float32), 0, 255).astype(np.uint8))
        self.room = room
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle([WX0 - 16, WY0 - 16, WX1 + 16, WY1 + 16], radius=26, outline=FRAME + (255,), width=32)
        cx = (WX0 + WX1) // 2
        d.rectangle([cx - 12, WY0, cx + 12, WY1], fill=FRAME + (255,))
        d.rectangle([WX0, WY0 + int(gh * 0.36) - 9, WX1, WY0 + int(gh * 0.36) + 9], fill=FRAME + (255,))
        d.rounded_rectangle([WX0 - 70, WY1, WX1 + 70, WY1 + 50], radius=10, fill=(92, 60, 52, 255))
        d.rectangle([WX0 - 70, WY1 + 38, WX1 + 70, WY1 + 50], fill=(66, 42, 40, 255))
        # candle body
        self.cx, self.cy = 1730, WY1 - 112
        d.rounded_rectangle([self.cx - 26, WY1 - 100, self.cx + 26, WY1], radius=8, fill=(250, 240, 220, 255))
        # fairy-light wire
        pts = [(x, 96 + 46 * math.sin(x / 120.0) ** 2 + x * 0.03) for x in range(0, WX0 - 10, 12)]
        d.line(pts, fill=(60, 54, 70, 255), width=4)
        self.overlay = ov
        self.glass_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(self.glass_mask).rounded_rectangle([WX0, WY0, WX1, WY1], radius=14, fill=255)
        # ---------- fairy bulbs (additive glow sprites, individual twinkle)
        self.bulbs = []
        spr_cols = [(255, 190, 90), (255, 220, 150), (255, 160, 110)]
        for x in range(50, WX0 - 40, 86):
            y = 96 + 46 * math.sin(x / 120.0) ** 2 + x * 0.03 + 16
            self.bulbs.append((int(x), int(y), _glow_sprite(46, spr_cols[int(rng.integers(0, 3))]),
                               int(rng.integers(12, 40)), rng.uniform(0, 6.28)))
        self.candle = _glow_sprite(150, (255, 170, 70))
        self.flame = _glow_sprite(22, (255, 236, 190))
        self.fk = [int(v) for v in rng.integers(40, 130, 3)]
        # ---------- mascot
        mp = os.path.join(HERE, "brand", "out", "driftlight_character_rgba.png")
        self.mascot = None
        if os.path.exists(mp):
            m = Image.open(mp).convert("RGBA")
            self.mascot = m.crop(m.getbbox())
        self.m_w = 500
        self.m_x = 1080
        self.breath_k = int(rng.integers(max(2, loop // 6), max(3, loop // 4)))
        self.font_z = ImageFont.truetype(os.path.join(FONT_DIR, "Inter-Bold.otf"), 60)

    @staticmethod
    def _add(arr, sprite, cx, cy, w):
        s = sprite.shape[0]
        x0, y0 = cx - s // 2, cy - s // 2
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + s), min(H, y0 + s)
        if xb <= xa or yb <= ya:
            return
        arr[ya:yb, xa:xb] += sprite[ya - y0:yb - y0, xa - x0:xb - x0] * w

    def frame(self, t):
        T = self.loop
        u = t / T
        # outside + twinkling bokeh
        win = self.outside.copy()
        for lay, k, ph in self.bokeh:
            win += lay * (0.55 + 0.45 * math.sin(2 * math.pi * k * u + ph))
        wim = Image.fromarray(np.clip(win, 0, 255).astype(np.uint8)).convert("RGBA")
        rl = Image.new("RGBA", (self.gw, self.gh), (0, 0, 0, 0))
        d = ImageDraw.Draw(rl)
        yy = ((self.rk * u + self.rph) % 1.0) * (self.gh + self.rlen) - self.rlen
        for x, y, l, a in zip(self.rx, yy, self.rlen, self.ra):
            d.line([(x, y), (x - l * 0.16, y + l)], fill=(222, 236, 255, int(a)), width=3)
        by = ((self.bk * u + self.bph) % 1.0) * (self.gh + 20) - 10
        for x, y, r in zip(self.bx, by, self.br):
            d.ellipse([x - r, y - r * 1.4, x + r, y + r * 1.4], fill=(200, 222, 255, 120))
            d.ellipse([x - r * 0.4, y - r * 0.9, x + r * 0.1, y - r * 0.3], fill=(255, 255, 255, 190))
        wim.alpha_composite(rl)
        fr = self.room.copy()
        fr.paste(wim.convert("RGB"), (WX0, WY0), self.glass_mask.crop((WX0, WY0, WX1, WY1)))
        fr.paste(self.overlay, (0, 0), self.overlay)
        # mascot breathing on the sill
        if self.mascot is not None:
            sc = 1 + 0.03 * math.sin(2 * math.pi * self.breath_k * u)
            mw = int(round(self.m_w * sc))
            mh = int(round(mw * self.mascot.height / self.mascot.width))
            m = self.mascot.resize((mw, mh), Image.LANCZOS)
            fr.paste(m, (self.m_x + (self.m_w - mw) // 2, WY1 + 34 - mh), m)
            zl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            zd = ImageDraw.Draw(zl)
            cyc = ((self.breath_k // 2 or 1) * u) % 1.0
            for k in range(3):
                v = (cyc - k * 0.22) % 1.0
                if v > 0.7:
                    continue
                a = int(255 * math.sin(math.pi * v / 0.7))
                zd.text((self.m_x - 30 - k * 30 - v * 26, WY1 + 34 - mh - 50 - k * 50 - v * 70), "z",
                        font=self.font_z.font_variant(size=40 + 12 * k), fill=(255, 236, 180, a))
            fr = Image.alpha_composite(fr.convert("RGBA"), zl).convert("RGB")
        # additive lights: fairy bulbs + candle
        arr = np.asarray(fr, np.float32).copy()
        for x, y, spr, k, ph in self.bulbs:
            self._add(arr, spr, x, y, 1.0 + 0.6 * math.sin(2 * math.pi * k * u + ph))
        fl = 0.8 + 0.1 * math.sin(2 * math.pi * self.fk[0] * u) + 0.07 * math.sin(2 * math.pi * self.fk[1] * u + 1) \
            + 0.05 * math.sin(2 * math.pi * self.fk[2] * u + 2)
        self._add(arr, self.candle, self.cx, self.cy, 0.55 * fl)
        self._add(arr, self.flame, self.cx, self.cy, 1.2 * fl)
        return np.clip(arr, 0, 255).astype(np.uint8)
