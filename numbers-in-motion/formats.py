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
    rv.draw_face(d, c, c, D, mood, t, (0.0, 0.0))
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
def quiz(vals, rounds, topic, year):
    F_T, F_N, F_V, F_S, F_VS = font(96, "Black"), font(70, "Bold"), font(104, "Black"), font(40, "SemiBold"), font(70, "Black")
    T_ASK, T_REV = 2.1, 1.7
    per = T_ASK + T_REV
    ev = []
    for ri, (a, b) in enumerate(rounds):
        t0 = ri * per
        ev.append((t0, "whoosh", 0.7))
        ev += [(t0 + 0.3 + 0.6 * j, "pop", 0.6) for j in range(3)]
        ev.append((t0 + T_ASK, "ding", 0.9))
    total = len(rounds) * per + 1.6
    ev.append((len(rounds) * per, "fanfare", 0.8))

    def frames():
        for fi in range(int(total * FPS)):
            t = fi / FPS
            img = rv.bg_image()
            d = ImageDraw.Draw(img)
            ri = min(int(t // per), len(rounds) - 1)
            lt = t - ri * per
            done = t >= len(rounds) * per
            band(d, 120, [("WHO SPENDS", (255, 255, 255)), ("MORE?", YEL)], F_T)
            ctext(d, W / 2, 290, f"{topic} · {year} · Round {ri + 1}/{len(rounds)}", F_S, rv.MUTED)
            a, b = rounds[ri]
            win = a if vals[a] > vals[b] else b
            rev = lt >= T_ASK or done
            rk = (lt - T_ASK) / 0.5 if not done else 1.0
            slide = ease(lt / 0.3) if not done else 1.0
            for j, e in enumerate((a, b)):
                cy = 640 + j * 640
                x_off = (1 - slide) * (W if j else -W)
                x0, x1, y0, y1 = 90 + x_off, W - 90 + x_off, cy - 230, cy + 230
                is_win = e == win
                d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=48, fill=SHADOW)
                oc = (GREEN if is_win else RED) if rev else INK
                d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=CARD, outline=oc, width=10 if rev else 6)
                mood = ("happy" if is_win else "worried") if rev else "neutral"
                bob = math.sin(t * 5 + j * 2) * 8 if not rev else (-(abs(math.sin(t * 9)) * 22) if is_win else 0)
                ball(img, e, x0 + 190, cy + bob, 230, mood, t)
                d.text((x0 + 350, cy - 130), short(e), font=F_N, fill=INK)
                if rev:
                    v = vals[e] * ease(rk)
                    d.text((x0 + 350, cy - 30), fmt(v, "$"), font=F_V, fill=GREEN if is_win else RED)
                    s = pop_scale(rk)
                    if s > 0.05:
                        check(d, x1 - 40, y0 + 40, 54 * s, is_win)
                else:
                    d.text((x0 + 350, cy - 30), "$ ???", font=F_V, fill=(190, 184, 170))
            # VS badge
            d.ellipse([W / 2 - 86, 960 - 86, W / 2 + 86, 960 + 86], fill=YEL, outline=INK, width=6)
            ctext(d, W / 2, 960 - 44, "VS", F_VS, INK)
            # timer / verdict
            if done:
                band(d, 1650, [("How many did you get?", (255, 255, 255)), ("↓", YEL)], font(66, "Black"), tilt=6)
            elif not rev:
                k = max(0.0, 1 - lt / T_ASK)
                d.rounded_rectangle([90, 1660, W - 90, 1712], radius=26, fill=(214, 207, 192), outline=INK, width=4)
                if k > 0.03:
                    d.rounded_rectangle([90, 1660, 90 + (W - 180) * k, 1712], radius=26, fill=YEL, outline=INK, width=4)
                ctext(d, W / 2, 1735, "Tap your guess…", F_S, rv.MUTED)
            else:
                ctext(d, W / 2, 1668, f"{short(win)} spends more", font(58, "Bold"), INK)
            yield img

    return frames(), total, ev


# ----------------------------------------------------------------------------- knockout
def knockout(vals, names, topic, year):
    F_T, F_N, F_BIG, F_S = font(70, "Black"), font(34, "Bold"), font(150, "Black"), font(40, "SemiBold")
    order = sorted(names, key=lambda e: vals[e])          # weakest first
    n = len(order)
    T0, GAP, HOLD = 1.2, 0.72, 2.6
    out_t = {e: T0 + GAP * (i + 1) for i, e in enumerate(order[:-1])}
    champ = order[-1]
    t_end = T0 + GAP * n
    total = t_end + HOLD
    ev = [(0.05, "whoosh", 0.7)] + [(tt, "bonk", 0.8) for tt in out_t.values()] + [(t_end, "fanfare", 0.9)]
    cols = 4
    import random
    rnd = random.Random(7)
    slots = list(names)
    rnd.shuffle(slots)
    pos = {e: (150 + (i % cols) * 260, 960 + (i // cols) * 270) for i, e in enumerate(slots)}
    spin = {e: rnd.choice((-1, 1)) * rnd.uniform(120, 260) for e in names}

    def thr(t):  # threshold: piecewise through each eliminated value
        if t <= T0:
            return vals[order[0]] * 0.5 * (t / T0)
        i = min(int((t - T0) / GAP), n - 2)
        k = min(1.0, (t - T0 - i * GAP) / GAP)
        lo = vals[order[i - 1]] if i > 0 else vals[order[0]] * 0.5
        return lo + (vals[order[i]] - lo) * k if t < t_end else vals[order[-2]]

    def frames():
        for fi in range(int(total * FPS)):
            t = fi / FPS
            img = rv.bg_image()
            d = ImageDraw.Draw(img)
            band(d, 110, [("LAST COUNTRY", (255, 255, 255)), ("STANDING", YEL)], F_T)
            ctext(d, W / 2, 262, f"{topic} · {year}", F_S, rv.MUTED)
            alive = [e for e in names if e == champ or t < out_t[e]]
            fin = t >= t_end
            # threshold panel
            d.rounded_rectangle([130 + 10, 350 + 12, W - 130 + 10, 760 + 12], radius=48, fill=SHADOW)
            d.rounded_rectangle([130, 350, W - 130, 760], radius=48, fill=CARD, outline=INK, width=6)
            if not fin:
                ctext(d, W / 2, 385, "To stay in, you need", F_S, rv.MUTED)
                ctext(d, W / 2, 440, fmt(thr(t), "$"), F_BIG, RED)
                ctext(d, W / 2, 655, f"{len(alive)} countries left" if len(alive) > 1 else "1 country left", font(48, "Bold"), INK)
            else:
                k = pop_scale((t - t_end) / 0.4)
                ctext(d, W / 2, 385, "WINNER", font(56, "Black"), GREEN)
                ctext(d, W / 2, 450, short(champ), font(int(120 * max(k, .2)), "Black"), INK)
                ctext(d, W / 2, 610, fmt(vals[champ], "$") + f" · more than #2–#{n if n < 10 else 4} combined?" if False else fmt(vals[champ], "$"), font(84, "Black"), GREEN)
            # balls
            for e in names:
                x, y = pos[e]
                D = 176
                if e != champ and t >= out_t[e]:
                    dt = t - out_t[e]
                    yy = y - 260 * dt + 2600 * dt * dt       # hop, then fall
                    if yy > H + 200:
                        continue
                    ball(img, e, x + spin[e] * 0.4 * dt, yy, D, "shocked", t, rot=spin[e] * dt)
                    if dt < 0.7:
                        lab = f"OUT · {fmt(vals[e], '$')}"
                        tw = d.textlength(lab, font=F_N)
                        d.rounded_rectangle([x - tw / 2 - 16, y - 28, x + tw / 2 + 16, y + 28], radius=20, fill=RED, outline=INK, width=4)
                        ctext(d, x, y - 22, lab, F_N, (255, 255, 255))
                    continue
                nxt = (not fin) and e == min(alive, key=lambda q: vals[q]) and e != champ
                if fin and e == champ:
                    k = ease((t - t_end) / 0.5)
                    x, y, D = x + (W / 2 - x) * k, y + (1330 - y) * k - abs(math.sin(t * 8)) * 30 * k, int(150 + 230 * k)
                    ball(img, e, x, y, D, "happy", t)
                    continue
                shake = math.sin(t * 40) * 7 if nxt else 0
                ball(img, e, x + shake, y + math.sin(t * 4 + x) * 6, D, "worried" if nxt else "neutral", t)
                ctext(d, x, y + 106, short(e), F_N, INK)
            if fin and t - t_end > 0.8:
                band(d, 1700, [("Who went out too early?", (255, 255, 255)), ("↓", YEL)], font(60, "Black"), tilt=6)
            yield img

    return frames(), total, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["quiz", "knockout"])
    ap.add_argument("--csv", default="data/military.csv")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--topic", default="Military budget")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    df = pd.read_csv(a.csv)
    vals = dict(df[df.year == a.year].set_index("entity").value)
    if a.mode == "quiz":
        fr, total, ev = quiz(vals, [("Germany", "India"), ("France", "Ukraine"), ("Saudi Arabia", "United Kingdom")], a.topic, a.year)
    else:
        top = sorted(vals, key=vals.get, reverse=True)[:12]
        fr, total, ev = knockout(vals, top, a.topic, a.year)
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
