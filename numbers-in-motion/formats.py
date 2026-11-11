#!/usr/bin/env python3
"""Alternative Shorts formats in the paper/sticker style: `quiz` (who spends more?) and `knockout`
(last country standing). Usage: formats.py quiz|knockout --out out/x.mp4"""
import argparse, math, os, subprocess, sys, tempfile
import pandas as pd
from PIL import Image, ImageDraw

import render_v2 as rv

rv.__dict__.update(rv.THEMES["paper"])
rv.W, rv.H = 1080, 1920
W, H, FPS = 1080, 1920, 30
NAVY, YEL, INK, CARD = (18, 30, 86), (255, 209, 64), (20, 26, 52), (255, 252, 244)
GREEN, RED, SHADOW = (38, 176, 104), (226, 74, 74), (196, 188, 170)
font, short, fmt = rv.font, rv.short, rv.fmt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))
import audio

_flags = {}


def ball(img, name, cx, cy, D, mood, t, alpha=1.0, rot=0.0):
    """Sticker: shadow, white ring, flag, dark outline, face."""
    key = (name, D)
    if key not in _flags:
        _flags[key] = rv.load_flag(name, D)
    S = D + 60
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = S / 2
    d.ellipse([c - D / 2 - 6, c - D / 2 + 2, c + D / 2 + 18, c + D / 2 + 26], fill=SHADOW + (255,))
    d.ellipse([c - D / 2 - 12, c - D / 2 - 12, c + D / 2 + 12, c + D / 2 + 12], fill=(255, 255, 255, 255), outline=INK + (255,), width=5)
    if _flags[key] is not None:
        lay.paste(_flags[key], (int(c - D / 2), int(c - D / 2)), _flags[key])
    d.ellipse([c - D / 2, c - D / 2, c + D / 2, c + D / 2], outline=INK + (255,), width=4)
    rv.draw_face(d, c, c, D, mood, t + 0.2, (0.0, 0.0))  # +0.2: no blink on frame 0
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(lay, (int(cx - S / 2), int(cy - S / 2)), lay)


def ctext(d, cx, y, txt, f, fill):
    d.text((cx - d.textlength(txt, font=f) / 2, y), txt, font=f, fill=fill)


def band(d, y, words, f, tilt=10):
    """Title on a tilted navy band; words = [(text, colour)]."""
    tw = sum(d.textlength(w + " ", font=f) for w, _ in words)
    x0, h = (W - tw) / 2, f.size * 1.35
    d.polygon([(x0 - 50, y - 8 + tilt), (x0 + tw + 40, y - 8 - tilt), (x0 + tw + 50, y + h - tilt), (x0 - 40, y + h + tilt)], fill=NAVY)
    x = x0
    for w, col in words:
        d.text((x, y + f.size * 0.08), w, font=f, fill=col)
        x += d.textlength(w + " ", font=f)


def ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


def pop_scale(k):
    return rv.ease_out_back(max(0.0, min(1.0, k)))


def check(d, cx, cy, r, ok=True):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN if ok else RED, outline=INK, width=5)
    if ok:
        d.line([(cx - r * .45, cy), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .35)], fill=(255, 255, 255), width=int(r * .26), joint="curve")
    else:
        for s in (-1, 1):
            d.line([(cx - r * .38, cy - s * r * .38), (cx + r * .38, cy + s * r * .38)], fill=(255, 255, 255), width=int(r * .24))


# ----------------------------------------------------------------------------- quiz
SHORT_ROUNDS = [("United States", "India", "total"), ("Germany", "Saudi Arabia", "total"), ("United Kingdom", "Vietnam", "total"),
                ("Japan", "Iran", "total"), ("China", "United States", "pc")]
LONG_ROUNDS = [("Russia", "India", "total"), ("Indonesia", "Japan", "total"), ("Canada", "Brazil", "total"),
               ("Australia", "United Kingdom", "total"), ("Egypt", "Spain", "total"), ("Italy", "South Africa", "total"),
               ("France", "Poland", "total"), ("Germany", "Saudi Arabia", "total"), ("United Kingdom", "Vietnam", "total"),
               ("Japan", "Iran", "total"),
               ("Qatar", "United States", "pc"), ("Saudi Arabia", "Russia", "pc"), ("India", "France", "pc"),
               ("Sweden", "China", "pc"), ("Canada", "Germany", "pc")]


def vfmt(metric, v):
    if metric == "pc":
        return f"{v:.1f} t"
    return f"{v / 1000:.1f}B t" if v >= 1000 else f"{v:.0f}M t"


def fit_band(d, y, words, size, maxw, tilt=10):
    while True:
        f = font(size, "Black")
        if sum(d.textlength(w + " ", font=f) for w, _ in words) <= maxw or size <= 40:
            break
        size -= 4
    band(d, y, words, f, tilt)


def quiz(data, rounds, topic, year, horiz=False, verb="POLLUTES", endcard=0.0):
    """data: {metric: {entity: value}}; rounds: [(a, b, metric)]."""
    global W, H
    W, H = (1920, 1080) if horiz else (1080, 1920)
    rv.W, rv.H, rv._BGIMG = W, H, None
    F_N, F_V, F_S, F_VS = font(64 if horiz else 70, "Bold"), font(96 if horiz else 104, "Black"), font(38 if horiz else 40, "SemiBold"), font(70, "Black")
    T_ASK, T_REV = (3.4, 2.6) if horiz else (2.2, 1.6)
    per = T_ASK + T_REV
    n = len(rounds)
    T_OUT = 5.0 if horiz else 1.9
    quiz_end = n * per
    total = quiz_end + T_OUT + endcard
    ev = []
    for ri in range(n):
        t0 = ri * per
        ev.append((t0, "whoosh", 0.7))
        ev += [(t0 + 0.4 + (T_ASK - 0.5) / 3 * j, "pop", 0.6) for j in range(3)]
        ev.append((t0 + T_ASK, "ding", 0.9))
    ev.append((quiz_end, "fanfare", 0.8))
    first_pc = next((i for i, r in enumerate(rounds) if r[2] == "pc"), None)
    if horiz:
        rects = [(140, 250, 880, 850), (1040, 250, 1780, 850)]
        vs_c, bar_y, D = (W / 2, 550), 925, 250
    else:
        rects = [(90, 410, W - 90, 870), (90, 1050, W - 90, 1510)]
        vs_c, bar_y, D = (W / 2, 960), 1640, 230

    def card(img, d, e, rect, metric, rev, is_win, rk, t, j, slide):
        x0, y0, x1, y1 = rect
        off = (1 - slide) * (W if j else -W)
        x0, x1 = x0 + off, x1 + off
        d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=48, fill=SHADOW)
        oc = (GREEN if is_win else RED) if rev else INK
        d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=CARD, outline=oc, width=10 if rev else 6)
        mood = ("happy" if is_win else "worried") if rev else "neutral"
        bob = math.sin(t * 5 + j * 2) * 8 if not rev else (-(abs(math.sin(t * 9)) * 22) if is_win else 0)
        val = vfmt(metric, data[metric][e] * ease(rk)) if rev else "???"
        vc = (GREEN if is_win else RED) if rev else (190, 184, 170)
        if horiz:
            cx = (x0 + x1) / 2
            ball(img, e, cx, y0 + 190 + bob, D, mood, t)
            ctext(d, cx, y0 + 345, short(e), F_N, INK)
            ctext(d, cx, y0 + 440, val, F_V, vc)
        else:
            cy = (y0 + y1) / 2
            ball(img, e, x0 + 190, cy + bob, D, mood, t)
            nm, fn = short(e), F_N
            while d.textlength(nm, font=fn) > x1 - x0 - 390 and fn.size > 44:
                fn = font(fn.size - 4, "Bold")
            d.text((x0 + 350, cy - 130), nm, font=fn, fill=INK)
            d.text((x0 + 350, cy - 30), val, font=F_V, fill=vc)
        if rev:
            sc = pop_scale(rk)
            if sc > 0.05:
                check(d, x1 - 40, y0 + 40, 54 * sc, is_win)

    def frames():
        for fi in range(int(total * FPS)):
            t = fi / FPS
            img = rv.bg_image()
            d = ImageDraw.Draw(img)
            if t >= quiz_end + T_OUT:                                # clean end-screen hold (long)
                fit_band(d, 70, [("Thanks for playing!", (255, 255, 255)), ("Next quiz ↓", YEL)], 72, W - 300, tilt=6)
                yield img
                continue
            if t >= quiz_end:                                        # score card
                k = pop_scale((t - quiz_end) / 0.4)
                if horiz:
                    fit_band(d, 110, [("WHAT'S YOUR", (255, 255, 255)), ("SCORE?", YEL)], 110, W - 300)
                    rows = [(f"{n - 2}–{n}", "Carbon genius", GREEN), (f"{n - 6}–{n - 3}", "Pretty good", INK), (f"0–{n - 7}", "Watch it again", RED)]
                    d.rounded_rectangle([430 + 10, 360 + 12, 1490 + 10, 880 + 12], radius=48, fill=SHADOW)
                    d.rounded_rectangle([430, 360, 1490, 880], radius=48, fill=CARD, outline=INK, width=6)
                    for i, (rg, lab, col) in enumerate(rows[: max(1, int((t - quiz_end) / 0.5))]):
                        d.text((520, 420 + i * 150), rg, font=font(92, "Black"), fill=col)
                        d.text((900, 440 + i * 150), lab, font=font(60, "Bold"), fill=INK)
                    ctext(d, W / 2, 940, "Comment your score ↓", font(56, "Bold"), INK)
                else:
                    fit_band(d, 620, [("YOUR SCORE?", (255, 255, 255))], int(130 * max(k, .3)), W - 160)
                    ctext(d, W / 2, 860, f"? / {n}", font(260, "Black"), INK)
                    fit_band(d, 1250, [("Comment it", (255, 255, 255)), ("↓", YEL)], 84, W - 200, tilt=6)
                    ctext(d, W / 2, 1420, "Full 15-round quiz on the channel", F_S, rv.MUTED)
                yield img
                continue
            ri = min(int(t // per), n - 1)
            lt = t - ri * per
            a, b, metric = rounds[ri]
            pc = metric == "pc"
            words = [(f"WHO {verb} MORE", (255, 255, 255)), ("PER PERSON?", YEL)] if pc else [(f"WHO {verb}", (255, 255, 255)), ("MORE?", YEL)]
            fit_band(d, 60 if horiz else 120, words, 96, W - (500 if horiz else 110))
            sub = f"{topic} {'per person' if pc else ''} · {year} · Round {ri + 1}/{n}".replace("  ", " ")
            ctext(d, W / 2, 195 if horiz else 290, sub, F_S, rv.MUTED)
            vals = data[metric]
            win = a if vals[a] > vals[b] else b
            lose = b if win == a else a
            rev = lt >= T_ASK
            rk = (lt - T_ASK) / 0.5
            slide = 1.0 if ri == 0 else ease(lt / 0.3)   # frame 0 must already show the question
            for j, e in enumerate((a, b)):
                card(img, d, e, rects[j], metric, rev, e == win, rk, t, j, slide)
            d.ellipse([vs_c[0] - 86, vs_c[1] - 86, vs_c[0] + 86, vs_c[1] + 86], fill=YEL, outline=INK, width=6)
            ctext(d, vs_c[0], vs_c[1] - 44, "VS", F_VS, INK)
            if pc and ri == first_pc and lt < T_ASK:                  # twist badge
                k = pop_scale(lt / 0.3)
                f = font(int(54 * max(k, .3)), "Black")
                tw = d.textlength("TWIST: PER PERSON", font=f)
                yb = bar_y - (150 if horiz else 96)
                if not horiz:
                    d.rounded_rectangle([W / 2 - tw / 2 - 30, yb - 12, W / 2 + tw / 2 + 30, yb + f.size + 22], radius=30, fill=RED, outline=INK, width=5)
                    ctext(d, W / 2, yb, "TWIST: PER PERSON", f, (255, 255, 255))
            bx0, bx1 = (360, W - 360) if horiz else (90, W - 90)
            if not rev:
                k = max(0.0, 1 - lt / T_ASK)
                d.rounded_rectangle([bx0, bar_y, bx1, bar_y + 52], radius=26, fill=(214, 207, 192), outline=INK, width=4)
                if k > 0.03:
                    d.rounded_rectangle([bx0, bar_y, bx0 + (bx1 - bx0) * k, bar_y + 52], radius=26, fill=YEL, outline=INK, width=4)
                ctext(d, W / 2, bar_y + 70, "Lock in your guess…", F_S, rv.MUTED)
            else:
                ratio = vals[win] / vals[lose]
                msg = f"{short(win)}: {ratio:.1f}× more" if ratio >= 1.2 else f"{short(win)} — by just {100 * (ratio - 1):.0f}%!"
                ctext(d, W / 2, bar_y - 4, msg, font(58, "Bold"), INK)
            yield img

    return frames(), total, ev


# ----------------------------------------------------------------------------- knockout
KO = dict(title=("LAST COUNTRY", "STANDING"), unit="internet users", hook="Who has the most people online?",
          payoff=("More people online than", "USA + Indonesia + Brazil", "+ Pakistan + Russia COMBINED"))


def knockout(vals, names, topic, year, horiz=False, endcard=0.0, cfg=KO):
    """Threshold rises; whoever is under it drops out. Short: 12 countries ~21 s. Long: 40 countries ~3 min."""
    global W, H
    W, H = (1920, 1080) if horiz else (1080, 1920)
    rv.W, rv.H, rv._BGIMG = W, H, None
    order = sorted(names, key=lambda e: vals[e])          # weakest first
    n = len(order)
    champ = order[-1]
    # ---- timeline
    T0 = 3.0 if horiz else 1.0
    out_t, pauses, t = {}, [], T0
    for i, e in enumerate(order[:-1]):
        left = n - i
        if horiz:
            gap = 3.2 if left > 10 else (5.0 if left > 3 else 8.0)
        else:
            gap = 1.3 if left > 4 else (1.8 if left > 2 else 2.4)
        if horiz and left in (10, 3):                      # stage banner before this round
            pauses.append((t, t + 3.0, "TOP 10 · Guess the winner!" if left == 10 else "FINAL 3"))
            t += 3.0
        t += gap
        out_t[e] = t
    t_end = t
    FIN = 8.0 if horiz else 4.2
    total = t_end + FIN + endcard
    ev = [(0.05, "whoosh", 0.7)] + [(tt, "bonk", 0.8) for tt in out_t.values()] + [(a, "ding", 0.7) for a, _, _ in pauses] + [(t_end, "fanfare", 0.9)]
    starts = [T0] + [out_t[e] for e in order[:-1]]       # threshold climbs to order[i] by out_t[order[i]]

    def thr(t):
        if t <= T0:
            return vals[order[0]] * (0.3 + 0.3 * ease(t / T0))
        for i, e in enumerate(order[:-1]):
            if t < out_t[e]:
                a = starts[i]
                for p0, p1, _ in pauses:                    # hold the threshold during a banner
                    if a <= p0 < out_t[e]:
                        if t < p1:
                            return vals[order[i - 1]] if i else vals[order[0]] * 0.6
                        a = p1
                lo = vals[order[i - 1]] if i else vals[order[0]] * 0.6
                return lo + (vals[e] - lo) * ease((t - a) / (out_t[e] - a))
        return vals[order[-2]]

    # ---- layout
    import random
    rnd = random.Random(7)
    slots = list(names)
    rnd.shuffle(slots)
    if horiz:
        cols, D, F_N, F_T, F_S, F_BIG = 8, 100, font(25, "Bold"), font(72, "Black"), font(34, "SemiBold"), font(118, "Black")
        pos = {e: (760 + (i % cols) * 150, 290 + (i // cols) * 170) for i, e in enumerate(slots)}
        panel = (60, 250, 640, 760)
    else:
        cols, D, F_N, F_T, F_S, F_BIG = 4, 176, font(34, "Bold"), font(70, "Black"), font(40, "SemiBold"), font(150, "Black")
        pos = {e: (150 + (i % cols) * 260, 980 + (i // cols) * 270) for i, e in enumerate(slots)}
        panel = (130, 380, W - 130, 800)
    spin = {e: rnd.choice((-1, 1)) * rnd.uniform(120, 260) for e in names}
    pcx = (panel[0] + panel[2]) / 2

    def frames():
        for fi in range(int(total * FPS)):
            t = fi / FPS
            img = rv.bg_image()
            d = ImageDraw.Draw(img)
            if t >= t_end + FIN:                            # clean end-screen hold (long)
                fit_band(d, 70, [("Thanks for watching!", (255, 255, 255)), ("Next video ↓", YEL)], 72, W - 300, tilt=6)
                yield img
                continue
            band(d, 40 if horiz else 110, [(cfg["title"][0], (255, 255, 255)), (cfg["title"][1], YEL)], F_T)
            ctext(d, W / 2, 152 if horiz else 262, f"{topic} · {year}", F_S, rv.MUTED)
            if not horiz:
                ctext(d, W / 2, 312, cfg["hook"], font(46, "Bold"), INK)
            alive = [e for e in names if e == champ or t < out_t[e]]
            fin = t >= t_end
            x0, y0, x1, y1 = panel
            d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=48, fill=SHADOW)
            d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=CARD, outline=INK, width=6)
            ph = y1 - y0
            if not fin:
                ctext(d, pcx, y0 + ph * .08, "To stay in, you need", F_S, rv.MUTED)
                ctext(d, pcx, y0 + ph * .2, fmt(thr(t)), F_BIG, RED)
                ctext(d, pcx, y0 + ph * .56, cfg["unit"], F_S, rv.MUTED)
                ctext(d, pcx, y0 + ph * .74, f"{len(alive)} countries left" if len(alive) > 1 else "1 country left", font(48, "Bold"), INK)
            else:
                k = pop_scale((t - t_end) / 0.4)
                ctext(d, pcx, y0 + ph * .07, "WINNER", font(56, "Black"), GREEN)
                ctext(d, pcx, y0 + ph * .17, short(champ), font(int((100 if horiz else 120) * max(k, .2)), "Black"), INK)
                ctext(d, pcx, y0 + ph * .42, fmt(vals[champ]) + " users", font(72, "Black"), GREEN)
                if t - t_end > 1.0:
                    for j, ln in enumerate(cfg["payoff"]):
                        ctext(d, pcx, y0 + ph * (.63 + .095 * j), ln, font(32 if horiz else 38, "Bold" if j == 0 else "Black"), INK)
            for p0, p1, txt in pauses:                       # stage card inside the panel
                if p0 <= t < p1:
                    k = pop_scale((t - p0) / 0.35)
                    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=NAVY, outline=INK, width=6)
                    a, _, b = txt.partition(" · ")
                    ctext(d, pcx, y0 + ph * (.22 if b else .32), a, font(int(110 * max(k, .3)), "Black"), YEL)
                    if b:
                        ctext(d, pcx, y0 + ph * .6, b, font(50, "Bold"), (255, 255, 255))
            for e in names:
                x, y = pos[e]
                if e != champ and t >= out_t[e]:
                    dt = t - out_t[e]
                    yy = y - 260 * dt + 2600 * dt * dt
                    if yy > H + 200:
                        continue
                    ball(img, e, x + spin[e] * 0.4 * dt, yy, D, "shocked", t, rot=spin[e] * dt)
                    if dt < (1.2 if horiz else 0.8):
                        lab = f"OUT · {fmt(vals[e])}"
                        tw = d.textlength(lab, font=F_N)
                        lx = min(max(x, tw / 2 + 24), W - tw / 2 - 24)
                        d.rounded_rectangle([lx - tw / 2 - 14, y - 26, lx + tw / 2 + 14, y + 26], radius=18, fill=RED, outline=INK, width=4)
                        ctext(d, lx, y - F_N.size * .62, lab, F_N, (255, 255, 255))
                    continue
                nxt = (not fin) and e == min(alive, key=lambda q: vals[q]) and e != champ
                if fin and e == champ:
                    k = ease((t - t_end) / 0.6)
                    tx, ty = (1290, 640) if horiz else (W / 2, 1330)
                    x, y = x + (tx - x) * k, y + (ty - y) * k - abs(math.sin(t * 8)) * 30 * k
                    ball(img, e, x, y, int(D + (300 if horiz else 230) * k), "happy", t)
                    continue
                shake = math.sin(t * 40) * 6 if nxt else 0
                ball(img, e, x + shake, y + math.sin(t * 4 + x) * 5, D, "worried" if nxt else "neutral", t)
                ctext(d, x, y + D * .6, short(e), F_N, INK)
            if fin and t - t_end > 1.2:
                if horiz:
                    fit_band(d, 960, [("Did you guess it?", (255, 255, 255)), ("Comment ↓", YEL)], 60, W - 300, tilt=6)
                else:
                    band(d, 1700, [("Did you guess it?", (255, 255, 255)), ("↓", YEL)], font(60, "Black"), tilt=6)
            yield img

    return frames(), total, ev


def ko_thumb(vals, out):
    global W, H
    W, H = 1280, 720
    rv.W, rv.H, rv._BGIMG = W, H, None
    img = rv.bg_image()
    d = ImageDraw.Draw(img)
    fit_band(d, 36, [("LAST COUNTRY", (255, 255, 255)), ("STANDING", YEL)], 104, W - 120, tilt=8)
    d.rounded_rectangle([60 + 8, 210 + 10, 560 + 8, 650 + 10], radius=40, fill=SHADOW)
    d.rounded_rectangle([60, 210, 560, 650], radius=40, fill=CARD, outline=INK, width=7)
    ctext(d, 310, 236, "To stay in, you need", font(38, "SemiBold"), rv.MUTED)
    ctext(d, 310, 300, "200M", font(150, "Black"), RED)
    ctext(d, 310, 500, "internet users", font(42, "Bold"), INK)
    ctext(d, 310, 562, "4 countries left", font(42, "Black"), INK)
    for e, (x, y), mood, D in (("India", (760, 330), "worried", 200), ("United States", (1080, 300), "shocked", 190),
                               ("Indonesia", (900, 560), "shocked", 170), ("China", (1160, 560), "neutral", 160)):
        ball(img, e, x, y, D, mood, 0.3)
    f = font(64, "Black")
    tw = d.textlength("WHO SURVIVES?", font=f)
    d.rounded_rectangle([960 - tw / 2 - 30, 640, 960 + tw / 2 + 30, 712], radius=30, fill=RED, outline=INK, width=5)
    ctext(d, 960, 640, "WHO SURVIVES?", f, (255, 255, 255))
    img.save(out, quality=92)
    print("->", out)


def thumb(data, out):
    global W, H
    W, H = 1280, 720
    rv.W, rv.H, rv._BGIMG = W, H, None
    img = rv.bg_image()
    d = ImageDraw.Draw(img)
    fit_band(d, 40, [("WHO POLLUTES", (255, 255, 255)), ("MORE?", YEL)], 120, W - 120, tilt=8)
    for j, (e, x) in enumerate((("Germany", 300), ("Saudi Arabia", 980))):
        d.rounded_rectangle([x - 230 + 8, 250 + 10, x + 230 + 8, 660 + 10], radius=44, fill=SHADOW)
        d.rounded_rectangle([x - 230, 250, x + 230, 660], radius=44, fill=CARD, outline=INK, width=7)
        ball(img, e, x, 400, 230, "smug" if j else "worried", 0.3)
        ctext(d, x, 540, short(e), font(54, "Bold"), INK)
        ctext(d, x, 600, "???", font(40, "Black"), (170, 164, 150))
    d.ellipse([640 - 100, 430 - 100, 640 + 100, 430 + 100], fill=YEL, outline=INK, width=7)
    ctext(d, 640, 430 - 52, "VS", font(84, "Black"), INK)
    f = font(46, "Black")
    tw = d.textlength("15 ROUNDS", font=f)
    d.rounded_rectangle([640 - tw / 2 - 26, 590, 640 + tw / 2 + 26, 664], radius=30, fill=RED, outline=INK, width=5)
    ctext(d, 640, 598, "15 ROUNDS", f, (255, 255, 255))
    img.save(out, quality=92)
    print("->", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["quiz", "knockout", "thumb", "kothumb"])
    ap.add_argument("--n", type=int, default=12, help="knockout: number of countries")
    ap.add_argument("--csv", default="data/military.csv")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--topic", default="Military budget")
    ap.add_argument("--rounds", default="short", choices=["short", "long"])
    ap.add_argument("--horizontal", action="store_true")
    ap.add_argument("--endcard", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    df = pd.read_csv(a.csv)
    if a.mode in ("quiz", "thumb"):
        data = {m: dict(df.set_index("entity")[m]) for m in ("total", "pc")}
        if a.mode == "thumb":
            return thumb(data, a.out)
        fr, total, ev = quiz(data, SHORT_ROUNDS if a.rounds == "short" else LONG_ROUNDS, a.topic, a.year, a.horizontal, endcard=a.endcard)
    else:
        vals = dict(df[df.year == a.year].set_index("entity").value)
        if a.mode == "kothumb":
            return ko_thumb(vals, a.out)
        top = sorted(vals, key=vals.get, reverse=True)[:a.n]
        fr, total, ev = knockout(vals, top, a.topic, a.year, a.horizontal, a.endcard)
    tmp = tempfile.mkdtemp()
    silent, wav = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for im in fr:
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()
    audio.write_wav(wav, audio.mix(total, ev))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("->", a.out, round(total, 1), "s")


if __name__ == "__main__":
    main()
