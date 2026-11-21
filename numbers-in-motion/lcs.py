#!/usr/bin/env python3
"""Last Country Standing 2.0: every UN country on screen, 10 rule rounds, one survivor.
Paper/sticker look. Long (1920x1080) or Short (1080x1920, a subset of rounds).

  python3 lcs.py long  --out out/lcs_ep1.mp4
  python3 lcs.py short --rounds 5 --out out/lcs_ep1_short.mp4
  python3 lcs.py frames --at 3,20,60 --out out/lcs_frames      # stills to check before a render
  python3 lcs.py thumb --out out/lcs_ep1_thumb.jpg
"""
import argparse, io, json, math, os, random, subprocess, sys, tempfile
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

import render_v2 as rv

rv.__dict__.update(rv.THEMES["paper"])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "shared"))
import audio, music  # noqa: E402

FPS = 30
NAVY, YEL, INK, CARD = (18, 30, 86), (255, 209, 64), (20, 26, 52), (255, 252, 244)
GREEN, RED, SHADOW, WHITE = (38, 176, 104), (226, 74, 74), (196, 188, 170), (255, 255, 255)
font = rv.font
EPN = os.environ.get("LCS_EP", "ep1")
EP = json.load(open(os.path.join(HERE, f"data/lcs/{EPN}.json")))
META = EP.get("meta", {})
CODE = {c["name"]: c["cca2"] for c in EP["countries"]}
LABEL = {c["name"]: c["label"] for c in EP["countries"]}
ORDER = [c["name"] for c in EP["countries"]]          # A→Z by label
UNIT1, UNITN = META.get("unit", ["country", "countries"])     # ep 4 (US states): "state", "states"
TOTAL = META.get("total", len(ORDER))
BRAND = META.get("brand", ["LAST COUNTRY", "STANDING"])
STICKER = META.get("sticker", 0.6)                            # sticker size as a share of its grid cell (when labels show)


def ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


def ease_io(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def pop(k):
    return rv.ease_out_back(max(0.0, min(1.0, k)))


# ----------------------------------------------------------------------------- sprites
@lru_cache(maxsize=None)
def flag(code, D):
    if META.get("flag_dir"):                                  # pre-cropped square stickers (us_flags_build.py)
        im = Image.open(os.path.join(HERE, "data/lcs", META["flag_dir"], f"{code}.jpg")).convert("RGBA").resize((D, D), Image.LANCZOS)
    else:
        import cairosvg
        p = os.path.join(rv.FLAG_DIR, f"{code}.svg")
        png = cairosvg.svg2png(url=p, output_width=D * 2, output_height=D * 2)
        im = Image.open(io.BytesIO(png)).convert("RGBA").resize((D, D), Image.LANCZOS)
    m = Image.new("L", (D, D), 0)
    ImageDraw.Draw(m).ellipse([0, 0, D - 1, D - 1], fill=255)
    im.putalpha(m)
    return im


@lru_cache(maxsize=6000)
def sprite(name, D, mood="neutral", ring=None):
    """Sticker: drop shadow, white ring, flag, outline, face. Returned centred in an (D+pad) square."""
    pad = max(16, D // 3)
    S = D + 2 * pad
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = S / 2
    rw = max(3, D // 14)
    lw = max(2, D // 30)
    d.ellipse([c - D / 2 - rw + D * .05, c - D / 2 - rw + D * .07, c + D / 2 + rw + D * .05, c + D / 2 + rw + D * .07], fill=SHADOW + (255,))
    d.ellipse([c - D / 2 - rw, c - D / 2 - rw, c + D / 2 + rw, c + D / 2 + rw], fill=(ring or WHITE) + (255,), outline=INK + (255,), width=lw)
    f = flag(CODE[name], D)
    lay.paste(f, (int(c - D / 2), int(c - D / 2)), f)
    d.ellipse([c - D / 2, c - D / 2, c + D / 2, c + D / 2], outline=INK + (255,), width=lw)
    if D >= 40:
        rv.draw_face(d, c, c, D, mood, 0.3)
    return lay


MOTION = os.environ.get("LCS_MOTION", "1") == "1"


def put(img, spr, x, y, alpha=1.0, rot=0.0, sx=1.0, sy=1.0):
    if sx != 1.0 or sy != 1.0:
        spr = spr.resize((max(2, int(spr.width * sx)), max(2, int(spr.height * sy))), Image.BICUBIC)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC)
    if alpha < 1:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(spr, (int(x - spr.width / 2), int(y - spr.height / 2)), spr)


def ctext(d, cx, y, txt, f, fill):
    d.text((cx - d.textlength(txt, font=f) / 2, y), txt, font=f, fill=fill)


def fit(d, txt, size, maxw, weight="Black"):
    while size > 20 and d.textlength(txt, font=font(size, weight)) > maxw:
        size -= 2
    return font(size, weight)


def card(d, box, fill=CARD, r=36, w=5):
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 + 8, y0 + 10, x1 + 8, y1 + 10], radius=r, fill=SHADOW)
    d.rounded_rectangle(box, radius=r, fill=fill, outline=INK, width=w)


def band(d, cx, y, words, f, tilt=8):
    tw = sum(d.textlength(w + " ", font=f) for w, _ in words) - d.textlength(" ", font=f)
    x0, h = cx - tw / 2, f.size * 1.35
    d.polygon([(x0 - 40, y - 6 + tilt), (x0 + tw + 34, y - 6 - tilt), (x0 + tw + 40, y + h - tilt), (x0 - 34, y + h + tilt)], fill=NAVY)
    x = x0
    for w, col in words:
        d.text((x, y + f.size * 0.08), w, font=f, fill=col)
        x += d.textlength(w + " ", font=f)


def xmark(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED, outline=INK, width=max(3, int(r * .14)))
    for s in (-1, 1):
        d.line([(cx - r * .4, cy - s * r * .4), (cx + r * .4, cy + s * r * .4)], fill=WHITE, width=max(3, int(r * .26)))


def sub_button(img, d, cx, cy, t0, t, scale=1.0, line="Subscribe to see who wins next episode"):
    """Animated SUBSCRIBE pill: pops in, a cursor taps it at +1.2 s, it turns grey 'SUBSCRIBED' with a bell ring."""
    k = pop((t - t0) / 0.45)
    if k <= 0.02:
        return
    s = scale * k
    tap = t - t0 - 1.2
    pressed = tap > 0.15
    press_k = 0.92 if 0 < tap < 0.15 else 1.0
    w, h = 430 * s * press_k, 96 * s * press_k
    fill = (110, 110, 118) if pressed else (230, 33, 23)
    d.rounded_rectangle([cx - w / 2 + 6, cy - h / 2 + 8, cx + w / 2 + 6, cy + h / 2 + 8], radius=h / 2, fill=SHADOW)
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h / 2, fill=fill, outline=INK, width=max(3, int(5 * s)))
    txt = "SUBSCRIBED" if pressed else "SUBSCRIBE"
    f = font(max(12, int(46 * s * press_k)), "Black")
    ctext(d, cx - 22 * s, cy - f.size * 0.62, txt, f, WHITE)
    # bell
    bx, by, br = cx + w / 2 - 52 * s, cy, 20 * s
    ang = math.sin((t - t0 - 1.35) * 25) * 0.5 if 0 < tap < 1.0 else 0
    pts = []
    for a in range(0, 181, 15):
        r = math.radians(a)
        pts.append((bx + math.cos(r + math.pi) * br, by - math.sin(r) * br * 0.9))
    pts += [(bx + br * 1.15, by + br * 0.55), (bx - br * 1.15, by + br * 0.55)]
    c, sn = math.cos(ang), math.sin(ang)
    pts = [(bx + (x - bx) * c - (y - by) * sn, by + (x - bx) * sn + (y - by) * c) for x, y in pts]
    d.polygon(pts, fill=WHITE)
    d.ellipse([bx - br * .28, by + br * .5, bx + br * .28, by + br * 1.0], fill=WHITE)
    # cursor (arrow) moving in to tap
    if -0.8 < tap < 0.9:
        mk = ease((tap + 0.8) / 0.8)
        mx, my = cx + 260 * s - 200 * s * mk, cy + 140 * s - 110 * s * mk
        arrow = [(mx, my), (mx, my + 46 * s), (mx + 12 * s, my + 34 * s), (mx + 22 * s, my + 54 * s),
                 (mx + 30 * s, my + 50 * s), (mx + 20 * s, my + 30 * s), (mx + 36 * s, my + 30 * s)]
        d.polygon(arrow, fill=WHITE, outline=INK)
    if line and k > 0.6:
        fl = font(max(12, int(34 * scale)), "Black")
        ctext(d, cx, cy + h / 2 + 22 * scale, line, fl, INK)


# ----------------------------------------------------------------------------- layout
class Geo:
    def __init__(self, horiz):
        self.horiz = horiz
        self.W, self.H = (1920, 1080) if horiz else (1080, 1920)
        if horiz:
            self.grid = (650, 36, 1890, 1050)
            self.panel = (36, 36, 610, 1050)
        else:
            self.grid = (40, 800, 1040, 1850)
            self.panel = (40, 150, 1040, 860)

    @lru_cache(maxsize=None)
    def layout(self, names):
        """names: tuple (A→Z). Returns {name: (x, y)}, D, show_label."""
        x0, y0, x1, y1 = self.grid
        w, h, n = x1 - x0, y1 - y0, len(names)
        best = None
        for cols in range(1, n + 1):
            rows = math.ceil(n / cols)
            cell = min(w / cols, h / rows)
            if best is None or cell > best[0]:
                best = (cell, cols, rows)
        cell, cols, rows = best
        lab = cell >= 118
        D = int(min(260, cell * (STICKER if lab else 0.8)))
        ox = x0 + (w - cols * cell) / 2 + cell / 2
        oy = y0 + (h - rows * cell) / 2 + cell / 2 - (cell * 0.08 if lab else 0)
        pos = {}
        for i, e in enumerate(names):
            r, c = divmod(i, cols)
            nrow = min(cols, n - r * cols)                   # centre a short last row
            cx = ox + c * cell + (cols - nrow) * cell / 2
            pos[e] = (cx, oy + r * cell)
        return pos, D, lab


# ----------------------------------------------------------------------------- timeline
class Episode:
    def __init__(self, kind, rounds=None):
        self.kind = kind
        self.horiz = kind == "long"
        self.g = Geo(self.horiz)
        long = self.horiz
        R = EP["rounds"]
        idx = list(range(len(R))) if rounds is None else rounds
        alive = list(ORDER)
        for i in range(idx[0]):                               # start from the field that reached the first round shown
            gone = {o["name"] for o in R[i]["out"]}
            alive = [e for e in alive if e not in gone]
        self.start_alive = tuple(alive)
        self.ev = []                                          # (t, sfx, gain)
        self.hits = []
        t = 0.0
        if long:
            self.intro = (0.0, 5.0, 13.0)                     # cold open until 5, rules card until 13
            t = 13.0
        else:
            self.intro = (0.0, 3.2, 3.2)
            t = 3.2
        self.ev.append((0.05, "whoosh", 0.8))
        self.rounds = []
        for i in idx:
            r = R[i]
            outs = [o["name"] for o in r["out"]]
            n = len(outs)
            T_CARD = 4.2 if long else 3.0
            T_GUESS = 5.5 if long else 3.2
            per = min(2.8, max(0.4, 16.0 / n)) if long else min(1.3, max(0.3, 11.0 / n))
            T_ELIM = n * per + 1.0
            T_CLOSE = (5.0 if long else 3.4) if r["close"] else 0.0
            T_FLOW = 2.0 if long else 1.6
            a = t
            b = a + T_CARD
            c = b + T_GUESS
            tout = {e: c + 0.4 + k * per for k, e in enumerate(outs)}
            dd = c + T_ELIM
            e_ = dd + T_CLOSE
            f_ = e_ + T_FLOW
            before = alive
            alive = [e for e in alive if e not in tout]
            self.rounds.append(dict(i=i, r=r, a=a, b=b, c=c, d=dd, e=e_, f=f_, tout=tout, before=tuple(before),
                                    after=tuple(alive), values={o["name"]: o["value"] for o in r["out"]}))
            self.ev.append((a + 0.05, "whoosh", 0.9))
            self.hits.append((a + 0.2, "impact"))
            for k in range(3):
                self.ev.append((b + 1.0 + k * (T_GUESS - 1.6) / 3, "pop", 0.7))
            g = 0.75 if n <= 6 else (0.55 if n <= 15 else 0.38)
            for e in outs:
                self.ev.append((tout[e], "bonk", g))
            if r["close"]:
                self.ev.append((dd + 0.1, "ding", 0.7))
            t = f_
        self.final_alive = tuple(alive)
        self.win = None
        if long:
            self.win = (t, t + 9.0, t + 15.0)                 # winner reveal, CTA, end
            self.ev.append((t + 0.1, "fanfare", 1.0))
            self.hits.append((t, "drop"))
            self.end = (t + 15.0, t + 27.0)                   # end-screen hold (12 s for YouTube end elements)
            self.total = t + 27.0
        else:
            if os.environ.get("LCS_WINNER") == "1" and len(alive) == 1:   # winner Short: crown, then the end card
                self.win = (t, t + 5.0, t + 5.0)
                self.ev.append((t + 0.1, "fanfare", 1.0))
                self.hits.append((t, "drop"))
                t += 5.0
            self.end = (t, t + 3.6)
            self.total = t + 3.6
            self.ev.append((t + 0.05, "ding", 0.8))

    # ---- state at time t
    def rnd_at(self, t):
        for R in self.rounds:
            if R["a"] <= t < R["f"]:
                return R
        return None

    def counter(self, t):
        R = self.rnd_at(t)
        if R is None:
            return len(self.final_alive)
        return len(R["before"]) - sum(1 for e, to in R["tout"].items() if t >= to)

    # ---- drawing
    def frame(self, t):
        g = self.g
        rv.W, rv.H, rv._BGIMG = g.W, g.H, getattr(self, "_bg", None)
        img = rv.bg_image()
        self._bg = rv._BGIMG
        d = ImageDraw.Draw(img)
        if t >= self.end[0] and self.horiz:
            return self.end_screen(img, d, t)
        R = self.rnd_at(t)
        self.draw_grid(img, d, t, R)
        self.draw_panel(img, d, t, R)
        if R and R["a"] <= t < R["b"]:
            self.round_card(img, d, t, R)
        if self.horiz and 0.3 <= t < self.intro[1]:
            k = pop((t - 0.3) / 0.35)
            gx = (g.grid[0] + g.grid[2]) / 2
            txt = META.get("teaser", "Even the USA is OUT by round 5!")
            f = fit(d, txt, int(64 * max(k, .2)), g.grid[2] - g.grid[0] - 100)
            tw = d.textlength(txt, font=f)
            d.rounded_rectangle([gx - tw / 2 - 36, 470, gx + tw / 2 + 36, 470 + f.size * 1.6], radius=30, fill=RED, outline=INK, width=6)
            ctext(d, gx, 470 + f.size * .22, txt, f, WHITE)
        if t < self.intro[2] and self.horiz and t >= self.intro[1]:
            self.rules_card(img, d, t)
        if not self.horiz and t >= self.end[0]:
            self.short_end(img, d, t)
        return img

    def grid_names(self, t, R):
        if R is None:
            return self.final_alive, None
        if t >= R["e"]:                                       # reflow
            return R["before"], (R["after"], ease_io((t - R["e"]) / (R["f"] - R["e"])))
        return R["before"], None

    def draw_grid(self, img, d, t, R):
        g = self.g
        if self.win and t >= self.win[0]:
            return self.draw_winner(img, d, t)
        names, flow = self.grid_names(t, R)
        if R is None and t < (self.rounds[0]["a"] if self.rounds else 0):
            names = self.start_alive
        pos, D, lab = g.layout(names)
        if flow:
            pos2, D2, lab2 = g.layout(flow[0])
            k = flow[1]
            Dk = int(round((D + (D2 - D) * k) / 2) * 2)
        close = R["r"]["close"]["name"] if (R and R["r"]["close"] and R["d"] <= t < R["f"]) else None
        intro_k = min(1.0, 0.6 + t / 1.2) if self.horiz else 1.0      # frame 0 already shows most flags
        fl = font(max(18, min(34, int(D * 0.24))), "Bold")
        n = len(names)
        tags = []
        for j, e in enumerate(names):
            x, y = pos[e]
            if intro_k < 1.0:                                 # cold-open wave
                kk = pop((intro_k * 1.5 - j / n * 0.9) * 3)
                if kk <= 0.01:
                    continue
                put(img, sprite(e, max(8, int(D * kk) // 2 * 2)), x, y)
                continue
            to = R["tout"].get(e) if R else None
            if to is not None and t >= to:                    # stamped, held, then falling
                dt = t - to
                hold = 0.9 if D >= 80 else 0.35
                if dt < hold:
                    if MOTION:
                        k = min(1.0, dt / 0.25)
                        shake = math.sin(dt * 70) * D * 0.07 * (1 - k)          # anticipation: shudder on the hit
                        sq = math.exp(-dt * 14) * math.cos(dt * 30) * 0.14       # squash, then spring back
                        hop = -D * 0.10 * ease(max(0.0, (dt - (hold - 0.18)) / 0.18))  # small rise right before the drop
                        put(img, sprite(e, D, "shocked"), x + shake, y + hop, sx=1 + sq, sy=1 - sq)
                    else:
                        put(img, sprite(e, D, "shocked"), x, y)
                    xmark(d, x + D * .32, y - D * .32, max(10, D * .28 * pop(dt / 0.25)))
                    if D >= 80:
                        tags.append((x, y, D, R["values"][e]))
                    continue
                ft = dt - hold
                yy = y - D * 1.4 * ft + 2600 * ft * ft
                if MOTION:
                    yy = y - D * 0.10 - D * 0.6 * ft + 3200 * ft * ft
                if yy < g.H + D:
                    rnd = random.Random(e)
                    put(img, sprite(e, D, "shocked"), x + rnd.uniform(-1, 1) * 160 * ft, yy, rot=rnd.choice((-1, 1)) * 220 * ft)
                continue
            if flow and e in pos2:
                x2, y2 = pos2[e]
                k = flow[1]
                x, y, DD, show = x + (x2 - x) * k, y + (y2 - y) * k, Dk, lab2 if k > 0.5 else lab
            else:
                DD, show = D, lab
            mood = "neutral"
            if R and R["b"] <= t < R["c"]:
                mood = "worried" if (hash(e) + int(t * 2)) % 5 == 0 else "neutral"
            if R and R["d"] <= t < R["e"] + 1.0:
                mood = "happy"
            ring = YEL if e == close else None
            yb = y + (math.sin(t * 3.2 + j * 0.7) * DD * 0.03 if DD >= 60 else 0)
            if e == close and R["d"] <= t < R["e"]:
                yb -= abs(math.sin((t - R["d"]) * 7)) * DD * 0.12
            fx = fy = 0.0
            if MOTION and R and R["c"] <= t < R["d"] + 0.5:
                for o, to2 in R["tout"].items():
                    dt2 = t - to2
                    if 0 <= dt2 < 0.45 and o in pos:
                        ox, oy = pos[o]
                        dx, dy = x - ox, y - oy
                        dist = math.hypot(dx, dy)
                        if 0 < dist < DD * 2.2:
                            f = DD * 0.10 * math.sin(dt2 / 0.45 * math.pi) * (1 - dist / (DD * 2.2))
                            fx += dx / dist * f
                            fy += dy / dist * f
                            mood = "shocked" if dt2 < 0.3 else mood
            put(img, sprite(e, DD, mood, ring), x + fx, yb + fy)
            if show:
                fl2 = font(max(18, min(38, int(DD * 0.22))), "Bold")
                txt = LABEL[e]
                ff = fl2 if d.textlength(txt, font=fl2) < DD * 1.9 else font(max(16, int(fl2.size * .8)), "Bold")
                while ff.size > 13 and d.textlength(txt, font=ff) > DD / STICKER * 0.97:      # never run into the next cell
                    ff = font(ff.size - 1, "Bold")
                ctext(d, x, yb + DD * 0.62, txt, ff, INK)
        for x, y, D_, v in tags:
            fv = font(30 if self.horiz else 34, "Black")
            tw = d.textlength(v, font=fv)
            lx = min(max(x, g.grid[0] + tw / 2 + 20), g.grid[2] - tw / 2 - 20)
            ly = max(8, y - D_ * 0.85)
            d.rounded_rectangle([lx - tw / 2 - 16, ly - 4, lx + tw / 2 + 16, ly + fv.size * 1.3], radius=18, fill=RED, outline=INK, width=4)
            ctext(d, lx, ly + 2, v, fv, WHITE)

    def draw_winner(self, img, d, t):
        g = self.g
        w0, w1, w2 = self.win
        e = self.final_alive[0]
        x0, y0, x1, y1 = g.grid
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 40
        k = ease((t - w0) / 0.9)
        pos, D, _ = g.layout(self.final_alive)
        sx, sy = pos[e]
        DD = int((D + (380 - D) * k) // 2 * 2)
        x, y = sx + (cx - sx) * k, sy + (cy - sy) * k - abs(math.sin(t * 5)) * 18 * k
        rnd = random.Random(int(t * FPS) // 2)
        for c in range(70):                                  # confetti
            rc = random.Random(c)
            st = w0 + rc.uniform(0, 1.2)
            if t < st:
                continue
            ft = (t - st) % 6.0
            px = x0 + rc.uniform(0, x1 - x0) + math.sin(ft * 2 + c) * 30
            py = y0 - 40 + ft * rc.uniform(120, 260)
            col = rc.choice([YEL, RED, GREEN, NAVY, (91, 155, 255)])
            s = rc.uniform(8, 16)
            d.rectangle([px, py, px + s, py + s * 0.6], fill=col)
        put(img, sprite(e, max(40, DD), "happy", YEL), x, y)
        # crown
        if k > 0.6:
            kk = pop((t - w0 - 0.6) / 0.5)
            cw, ch = 170 * kk, 110 * kk
            by = y - DD / 2 - 30
            pts = [(x - cw / 2, by), (x - cw / 2, by - ch), (x - cw / 4, by - ch * .55), (x, by - ch * 1.1), (x + cw / 4, by - ch * .55),
                   (x + cw / 2, by - ch), (x + cw / 2, by)]
            d.polygon(pts, fill=YEL, outline=INK, width=6)
        ctext(d, cx, cy + 240, LABEL[e].upper(), font(96, "Black"), INK)
        ctext(d, cx, cy + 360, f"Last {UNIT1} standing", font(42, "Bold"), rv.MUTED)

    def draw_panel(self, img, d, t, R):
        g = self.g
        x0, y0, x1, y1 = g.panel
        cx = (x0 + x1) / 2
        hz = self.horiz
        # title band
        band(d, cx, y0 + 6 if hz else 40, [(BRAND[0], WHITE), (BRAND[1], YEL)], font(42 if hz else 60, "Black"))
        top = y0 + 110 if hz else y0
        # round pill
        if R:
            ri, nr = R["i"] + 1, len(EP["rounds"])
            txt = f"ROUND {ri} / {nr}"
            f = font(40 if hz else 46, "Black")
            tw = d.textlength(txt, font=f)
            d.rounded_rectangle([cx - tw / 2 - 26, top, cx + tw / 2 + 26, top + 62], radius=31, fill=RED, outline=INK, width=4)
            ctext(d, cx, top + 6, txt, f, WHITE)
            dw = 30
            for q in range(nr):                               # progress dots
                qx = cx - (nr - 1) * dw / 2 + q * dw
                fillc = INK if q < R["i"] else (RED if q == R["i"] else CARD)
                d.ellipse([qx - 9, top + 78, qx + 9, top + 96], fill=fillc, outline=INK, width=3)
        elif self.win and t >= self.win[0]:
            pass
        # rule / close-call / intro card
        cb = (x0 + 10, top + 120, x1 - 10, top + (450 if hz else 500))
        if R and t >= R["b"]:
            if R["r"]["close"] and R["d"] <= t < R["f"]:
                self.close_card(img, d, t, R, cb)
            else:
                self.rule_card(d, R, cb)
        elif t < (self.rounds[0]["a"] if self.rounds else 0):
            card(d, cb)
            bx = (cb[0] + cb[2]) / 2
            if hz:
                ctext(d, bx, cb[1] + 36, f"{TOTAL} {UNITN}.", font(58, "Black"), INK)
                ctext(d, bx, cb[1] + 110, "10 rounds.", font(58, "Black"), INK)
                ctext(d, bx, cb[1] + 184, "1 survivor.", font(58, "Black"), RED)
                ctext(d, bx, cb[1] + 268, "Does yours make it?", font(36, "Bold"), rv.MUTED)
            else:
                ctext(d, bx, cb[1] + 40, f"{len(self.start_alive)} {UNITN} left.", font(64, "Black"), INK)
                ctext(d, bx, cb[1] + 150, "Who's OUT next?", font(72, "Black"), RED)
        elif self.win and t >= self.win[0]:
            card(d, cb, fill=NAVY)
            bx = (cb[0] + cb[2]) / 2
            ctext(d, bx, cb[1] + 34, "WINNER", font(44, "Black"), YEL)
            ctext(d, bx, cb[1] + 96, LABEL[self.final_alive[0]], font(84, "Black"), WHITE)
            wv = META.get("win_value") or EP["winner"]["value"]
            ctext(d, bx, cb[1] + 206, wv, fit(d, wv, 48, cb[2] - cb[0] - 40), YEL)
            ctext(d, bx, cb[1] + 268, META.get("win_note", ""), font(28, "SemiBold"), WHITE)
        # counter (replaced by the subscribe button once the winner is crowned)
        cy0 = cb[3] + (40 if hz else 30)
        if hz and self.win and t >= self.win[0] + 2.5:
            sub_button(img, d, cx, cy0 + 70, self.win[0] + 2.5, t, scale=1.0,
                       line="")
            ctext(d, cx, cy0 + 140, "to see who wins", font(34, "Black"), INK)
            ctext(d, cx, cy0 + 184, "the next episode!", font(34, "Black"), RED)
            return
        n = self.counter(t) if t >= (self.rounds[0]["a"] if self.rounds else 0) else len(self.start_alive)
        if hz:
            last = max([to for to in (R["tout"].values() if R else []) if to <= t] or [-9])
            pk = max(0.0, 1 - (t - last) / 0.18) if MOTION else 0.0
            ctext(d, cx, cy0 - 10 - 8 * pk, str(n), font(int(128 * (1 + 0.15 * pk)), "Black"), RED if pk > 0.3 else INK)
            ctext(d, cx, cy0 + 138, f"{UNITN} left" if n != 1 else f"{UNIT1} left", font(36, "Bold"), rv.MUTED)
        else:
            last = max([to for to in (R["tout"].values() if R else []) if to <= t] or [-9])
            pk = max(0.0, 1 - (t - last) / 0.18) if MOTION else 0.0
            f = font(int(120 * (1 + 0.15 * pk)), "Black")
            s = str(n)
            sw = d.textlength(s, font=f)
            lab = f"{UNITN} left" if n != 1 else f"{UNIT1} left"
            lw = d.textlength(lab, font=font(44, "Bold"))
            sx = cx - (sw + 24 + lw) / 2
            d.text((sx, cy0 - 10 * pk), s, font=f, fill=RED if pk > 0.3 else INK)
            d.text((sx + sw + 24, cy0 + 62), lab, font=font(44, "Bold"), fill=rv.MUTED)
        # ticker of recent outs (long only)
        if hz and R and t >= R["c"]:
            gone = [(e, to) for e, to in R["tout"].items() if t >= to]
            ty = cy0 + 200
            ctext(d, cx, ty, f"OUT this round: {len(gone)}", font(30, "Black"), RED)
            for j, (e, to) in enumerate(reversed(gone[-3:])):
                yy = ty + 50 + j * 58
                a = min(1.0, (t - to) / 0.25)
                put(img, sprite(e, 44), x0 + 50, yy + 22, alpha=a)
                nm = LABEL[e]
                fn = fit(d, nm, 30, 250, "Bold")
                d.text((x0 + 86, yy + 4), nm, font=fn, fill=INK)
                v = R["values"][e]
                fv = font(28, "SemiBold")
                d.text((x1 - 16 - d.textlength(v, font=fv), yy + 6), v, font=fv, fill=RED)

    def rule_card(self, d, R, cb):
        card(d, cb)
        bx = (cb[0] + cb[2]) / 2
        a, b = R["r"]["rule"]
        w = cb[2] - cb[0] - 50
        ctext(d, bx, cb[1] + 26, "YOUR COUNTRY IS OUT IF IT HAS…" if False else "THE RULE", font(30, "Black"), rv.MUTED)
        fa = fit(d, a, 58 if self.horiz else 64, w)
        fb = fit(d, b, 58 if self.horiz else 64, w)
        ctext(d, bx, cb[1] + 78, a, fa, INK)
        ctext(d, bx, cb[1] + 78 + fa.size * 1.2, b, fb, RED)
        src = ("Source: " + R["r"]["source"]).split(" · ", 1)
        fs = font(24, "Medium")
        for j, ln in enumerate(src):
            ctext(d, bx, cb[3] - (40 if len(src) == 1 else 76) + j * 34, ln, fit(d, ln, 24, w, "Medium"), rv.MUTED)

    def close_card(self, img, d, t, R, cb):
        card(d, cb, fill=YEL)
        bx = (cb[0] + cb[2]) / 2
        c = R["r"]["close"]
        k = pop((t - R["d"]) / 0.4)
        ctext(d, bx, cb[1] + 22, "CLOSEST CALL", font(int(52 * max(k, .3)), "Black"), INK)
        put(img, sprite(c["name"], 110, "worried"), cb[0] + 110, cb[1] + 200)
        nm = LABEL[c["name"]]
        d.text((cb[0] + 200, cb[1] + 120), nm, font=fit(d, nm, 56, cb[2] - cb[0] - 230), fill=INK)
        d.text((cb[0] + 200, cb[1] + 196), c["value"], font=fit(d, c["value"], 44, cb[2] - cb[0] - 230, "Bold"), fill=RED)
        ctext(d, bx, cb[3] - 62, "Survived by a hair!", font(36, "Black"), INK)

    def round_card(self, img, d, t, R):
        g = self.g
        k_in, k_out = (t - R["a"]) / 0.45, (R["b"] - t) / 0.35
        k = min(pop(k_in), ease(k_out))
        ov = Image.new("RGBA", (g.W, g.H), INK + (int(150 * min(1, k_in, k_out * 2)),))
        img.paste(ov, (0, 0), ov)
        d = ImageDraw.Draw(img)
        bw, bh = (1300, 560) if self.horiz else (960, 720)
        cx, cy = g.W / 2, g.H / 2
        s = max(0.05, k)
        box = (cx - bw / 2 * s, cy - bh / 2 * s, cx + bw / 2 * s, cy + bh / 2 * s)
        if s < 0.5:
            card(d, box, fill=NAVY)
            return
        card(d, box, fill=NAVY, r=48, w=7)
        a, b = R["r"]["rule"]
        nr = len(EP["rounds"])
        ctext(d, cx, box[1] + 40 * s, f"ROUND {R['i'] + 1} / {nr}", font(int(56 * s), "Black"), YEL)
        ctext(d, cx, box[1] + 120 * s, "Your country is OUT if it has…" if False else "New rule:", font(int(40 * s), "Bold"), WHITE)
        w = (bw - 120) * s
        fa = fit(d, a, int((96 if self.horiz else 92) * s), w)
        fb = fit(d, b, int((96 if self.horiz else 92) * s), w)
        ctext(d, cx, box[1] + 200 * s, a, fa, WHITE)
        ctext(d, cx, box[1] + 200 * s + fa.size * 1.2, b, fb, YEL)
        ctext(d, cx, box[3] - 70 * s, f"{len(R['before'])} {UNITN} left · is yours safe?", font(int(36 * s), "Bold"), WHITE)

    def rules_card(self, img, d, t):
        g = self.g
        a, b = self.intro[1], self.intro[2]
        k_in, k_out = (t - a) / 0.45, (b - t) / 0.35
        k = min(pop(k_in), ease(k_out))
        ov = Image.new("RGBA", (g.W, g.H), INK + (int(150 * min(1, k_in, k_out * 2)),))
        img.paste(ov, (0, 0), ov)
        d = ImageDraw.Draw(img)
        s = max(0.05, k)
        bw, bh = 1240, 640
        cx, cy = g.W / 2, g.H / 2
        box = (cx - bw / 2 * s, cy - bh / 2 * s, cx + bw / 2 * s, cy + bh / 2 * s)
        card(d, box, r=48, w=7)
        if s < 0.5:
            return
        ctext(d, cx, box[1] + 40 * s, "HOW IT WORKS", font(int(64 * s), "Black"), RED)
        lines = [("1", "Every round has a new rule."), ("2", f"Break the rule → your {UNIT1} is OUT."),
                 ("3", "All numbers are real. Sources on screen."), ("4", f"{UNITN.capitalize()} are A → Z. Find yours!")]
        for j, (n, txt) in enumerate(lines):
            yy = box[1] + (170 + j * 105) * s
            if t < a + 0.5 + j * 0.9:
                continue
            xx = box[0] + 110 * s
            d.ellipse([xx - 34 * s, yy, xx + 34 * s, yy + 68 * s], fill=NAVY)
            ctext(d, xx, yy + 8 * s, n, font(int(44 * s), "Black"), YEL)
            d.text((xx + 64 * s, yy + 6 * s), txt, font=font(int(48 * s), "Bold"), fill=INK)

    def short_end(self, img, d, t):
        g = self.g
        k = pop((t - self.end[0]) / 0.4)
        ov = Image.new("RGBA", (g.W, g.H), (238, 233, 222, int(200 * min(1.0, (t - self.end[0]) / 0.3))))
        img.paste(ov, (0, 0), ov)
        d = ImageDraw.Draw(img)
        bw, bh = 940 * k, 420 * k
        box = (g.W / 2 - bw / 2, 1180 - bh / 2, g.W / 2 + bw / 2, 1180 + bh / 2)
        card(d, box, fill=NAVY, r=48, w=7)
        if k > 0.6:
            ctext(d, g.W / 2, box[1] + 60, "Watch all 10 rounds" if self.win else "Who wins it all?", font(76, "Black"), YEL)
            ctext(d, g.W / 2, box[1] + 170, f"Full game ({TOTAL} → 1)", font(54, "Bold"), WHITE)
            ctext(d, g.W / 2, box[1] + 250, "on the channel ↑", font(54, "Bold"), WHITE)
        sub_button(img, d, g.W / 2, 1530, self.end[0] + 0.5, t, scale=1.25, line="")

    def end_screen(self, img, d, t):
        g = self.g
        band(d, g.W / 2, 90, [("Thanks for", WHITE), ("watching!", YEL)], font(80, "Black"))
        ctext(d, g.W / 2, 230, f"How far did YOUR {UNIT1} get? Tell us in the comments.", font(44, "Bold"), INK)
        for bx in ((g.W / 2 - 560, 420, g.W / 2 - 60, 700), (g.W / 2 + 60, 420, g.W / 2 + 560, 700)):
            d.rounded_rectangle(bx, radius=24, outline=SHADOW, width=4)   # where YouTube end-screen videos sit
        return img

    # winner CTA overlays the winner scene
    def cta(self, img, d, t):
        pass


# ----------------------------------------------------------------------------- render
_EPI = None


def _init(kind, rounds):
    global _EPI
    _EPI = Episode(kind, rounds)


def _render_chunk(args):
    f0, f1, path = args
    ep = _EPI
    W, H = ep.g.W, ep.g.H
    tmp = path[:-4] + ".part.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        im = ep.frame(fi / FPS)
        if ep.win and ep.win[1] <= fi / FPS < ep.end[0]:
            d = ImageDraw.Draw(im)
            band(d, (ep.g.grid[0] + ep.g.grid[2]) / 2, 940, [(f"How far did YOUR {UNIT1} get?", WHITE), ("Comment ↓", YEL)], font(50, "Black"))
        ff.stdin.write(im.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() == 0:
        os.replace(tmp, path)
    return path


def soundtrack(ep, wav):
    m = music.track(ep.total, "race", seed=11, hits=ep.hits)
    out = m * 0.5
    cache = {}
    for t0, name, gn in ep.ev:
        if name not in cache:
            cache[name] = audio.SFX[name]()
        s = int(t0 * audio.SR)
        y = cache[name] * gn
        if MOTION and name == "bonk":
            r = random.Random(int(t0 * 1000)).uniform(0.85, 1.18)          # no machine-gun repeats
            n = int(len(y) / r)
            y = np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y) * random.Random(int(t0 * 997)).uniform(0.8, 1.0)
        e = min(len(out), s + len(y))
        if s < len(out):
            out[s:e] += y[: e - s]
    out = out / (np.abs(out).max() + 1e-9) * 0.89
    audio.write_wav(wav, out)


def render(kind, rounds, out, jobs=2):
    ep = Episode(kind, rounds)
    nf = int(ep.total * FPS)
    tmp = tempfile.mkdtemp(prefix="lcs_")
    nchunk = max(jobs * 3, 6)
    bounds = [nf * k // nchunk for k in range(nchunk + 1)]
    parts = [(bounds[k], bounds[k + 1], os.path.join(tmp, f"c{k:02d}.mp4")) for k in range(nchunk)]
    with Pool(jobs, initializer=_init, initargs=(kind, rounds)) as p:
        done = p.map(_render_chunk, parts, chunksize=1)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{x}'\n" for x in done))
    silent, wav = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    soundtrack(ep, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", out + ".tmp.mp4"], check=True)
    os.replace(out + ".tmp.mp4", out)
    print("->", out, f"{ep.total:.1f}s")
    return ep


def thumb(out):
    W, H = 1280, 720
    rv.W, rv.H, rv._BGIMG = W, H, None
    img = rv.bg_image()
    d = ImageDraw.Draw(img)
    rnd = random.Random(3)
    names = list(ORDER)
    rnd.shuffle(names)
    cols, cell = 16, 80
    k = 0
    for r in range(9):
        for c in range(cols):
            e = names[k % len(names)]
            k += 1
            x, y = 40 + c * cell + (cell / 2 if r % 2 else 0), 40 + r * cell
            put(img, sprite(e, 58), x, y, alpha=0.55)
            if rnd.random() < 0.55:
                xmark(d, x + 16, y - 16, 15)
    var = os.environ.get("LCS_THUMB", "a")
    tint = {"a": (238, 233, 222, 120), "b": (255, 209, 64, 205), "c": (120, 190, 255, 205)}[var]
    ov = Image.new("RGBA", (W, H), tint)
    img.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(img)
    if var != "a":
        e0, w1, w2 = os.environ["LCS_THUMB_TXT"].split("|")          # country | white words | yellow words
        if var == "b":                                              # one giant shocked face + hook words
            put(img, sprite(e0, 400, "shocked"), 330, 420)
            xmark(d, 330 + 160, 420 - 160, 80)
            f1 = fit(d, w1, 150, 620)
            d.text((640, 200), w1, font=f1, fill=INK)
            f2 = fit(d, w2, 190, 520)
            tw = d.textlength(w2, font=f2)
            d.rounded_rectangle([630, 370, 660 + tw + 30, 370 + f2.size * 1.25], radius=30, fill=RED, outline=INK, width=8)
            d.text((660, 370 + f2.size * 0.06), w2, font=f2, fill=WHITE)
            band(d, W / 2, 30, [(str(TOTAL), YEL), (UNITN.upper() + " →", WHITE), ("1", YEL)], font(84, "Black"))
        else:                                                       # c: three faces, big question on top
            th = META.get("thumb")
            if os.environ.get("LCS_THUMB_FACES"):
                th = [[n, m] for n, m in zip(os.environ["LCS_THUMB_FACES"].split("|"), ("shocked", "worried", "shocked"))]
            for (e, mood), x, y, D in zip(th, (230, 640, 1050), (470, 500, 470), (260, 300, 260)):
                put(img, sprite(e, D, mood), x, y)
                xmark(d, x + D * .36, y - D * .36, D * .2)
            band(d, W / 2, 40, [(w1, WHITE), (w2, YEL)], fit(d, w1 + " " + w2, 120, 1100))
        img.convert("RGB").save(out, quality=92)
        print("->", out)
        return
    th = META.get("thumb", [["United States", "shocked"], ["Egypt", "worried"], ["China", "worried"]])
    for (e, mood), x, y, D in zip(th, (210, 640, 1080), (430, 470, 420), (230, 270, 230)):
        put(img, sprite(e, D, mood), x, y)
    xmark(d, 210 + 90, 430 - 90, 52)
    band(d, W / 2, 34, [(str(TOTAL), YEL), (UNITN.upper() + " →", WHITE), ("1", YEL)], font(96, "Black"))
    f = font(70, "Black")
    txt = META.get("thumb_pill", "WHO SURVIVES?")
    tw = d.textlength(txt, font=f)
    d.rounded_rectangle([W / 2 - tw / 2 - 34, 610, W / 2 + tw / 2 + 34, 700], radius=34, fill=RED, outline=INK, width=6)
    ctext(d, W / 2, 615, txt, f, WHITE)
    img.convert("RGB").save(out, quality=92)
    print("->", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["long", "short", "frames", "thumb"])
    ap.add_argument("--rounds", default=None, help="comma list of 1-based rounds (short)")
    ap.add_argument("--kind", default="long")
    ap.add_argument("--at", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    rounds = [int(x) - 1 for x in a.rounds.split(",")] if a.rounds else None
    if a.mode == "thumb":
        return thumb(a.out)
    if a.mode == "frames":
        ep = Episode(a.kind, rounds)
        os.makedirs(a.out, exist_ok=True)
        print("total", round(ep.total, 1), [(R["i"] + 1, round(R["a"], 1), round(R["f"], 1)) for R in ep.rounds])
        for s in a.at.split(","):
            t = float(s)
            ep.frame(t).convert("RGB").save(os.path.join(a.out, f"{a.kind}_{t:06.1f}.jpg"), quality=88)
        return
    render(a.mode, rounds, a.out, a.jobs)


if __name__ == "__main__":
    main()
