"""Racing bar chart v2: flags with cartoon faces, auto-detected story captions, history ticker,
intro question, outro reveal, and a generated soundtrack with sound effects.

Usage:
    python render_v2.py --csv data/population.csv --title "Most Populous Countries" \
        --subtitle "1952 – 2007 · Top 10" --source Gapminder --channel "Numbers in Motion" \
        --question "Who will be #2 in 2007?" --events data/population_events.csv \
        --out out/population_v2.mp4 --seed 3

Input CSV: entity, group, year, value   (group optional; drives bar colors)
Events CSV (optional): year, text       (real historical moments shown as a ticker)
"""
from __future__ import annotations

import argparse
import io
import math
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'shared'))
import audio

# ----------------------------------------------------------------------------- theme
W, H = 1920, 1080
BG = (14, 16, 22)
FG = (240, 240, 245)
MUTED = (140, 145, 160)
GRID = (40, 44, 56)
ACCENT = (255, 196, 61)
BUBBLE = (250, 250, 252)
BUBBLE_TXT = (20, 22, 30)

GROUP_COLORS = {
    "Asia": (255, 111, 97), "Europe": (91, 155, 255), "Africa": (255, 196, 61),
    "Americas": (87, 212, 148), "Oceania": (196, 132, 255), "Middle East": (73, 203, 227),
}
FALLBACK = [(255, 111, 97), (91, 155, 255), (255, 196, 61), (87, 212, 148),
            (196, 132, 255), (255, 159, 67), (73, 203, 227), (241, 109, 196)]

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
FLAG_DIR = os.path.join(HERE, "vendor/node_modules/flag-icons/flags/1x1")


def font(size, weight="SemiBold"):
    p = os.path.join(FONT_DIR, f"Inter-{weight}.otf")
    return ImageFont.truetype(p if os.path.exists(p) else os.path.join(FONT_DIR, "Inter-Regular.otf"), size)


F_TITLE, F_SUB = font(64, "Bold"), font(34, "Medium")
F_YEAR, F_LABEL, F_VALUE = font(190, "Bold"), font(38, "SemiBold"), font(34, "Medium")
F_RANK, F_SMALL, F_LEGEND = font(30, "Medium"), font(26, "Regular"), font(28, "Medium")
F_BUBBLE, F_TICK = font(31, "Bold"), font(32, "SemiBold")
F_Q, F_Q2 = font(78, "Bold"), font(40, "Medium")

# ----------------------------------------------------------------------------- names, flags
ISO_OVERRIDES = {
    "Korea, Rep.": "kr", "Korea, Dem. Rep.": "kp", "Congo, Dem. Rep.": "cd", "Congo, Rep.": "cg",
    "Iran": "ir", "Vietnam": "vn", "Taiwan": "tw", "Hong Kong, China": "hk", "Yemen, Rep.": "ye",
    "West Bank and Gaza": "ps", "Slovak Republic": "sk", "Reunion": "re", "Cote d'Ivoire": "ci",
    "Syria": "sy", "Tanzania": "tz", "Bolivia": "bo", "Venezuela": "ve", "Russia": "ru",
    "United States": "us", "United Kingdom": "gb", "Czech Republic": "cz", "Turkey": "tr",
}
SHORT = {"United States": "USA", "United Kingdom": "UK", "Korea, Rep.": "South Korea",
         "Congo, Dem. Rep.": "DR Congo", "Korea, Dem. Rep.": "North Korea"}


def iso2(name: str) -> str | None:
    if name in ISO_OVERRIDES:
        return ISO_OVERRIDES[name]
    try:
        import pycountry
        return pycountry.countries.lookup(name).alpha_2.lower()
    except Exception:
        return None


def short(name: str) -> str:
    return SHORT.get(name, name)


def load_flag(name: str, d: int) -> Image.Image | None:
    code = iso2(name)
    path = os.path.join(FLAG_DIR, f"{code}.svg") if code else ""
    if not code or not os.path.exists(path):
        return None
    import cairosvg
    png = cairosvg.svg2png(url=path, output_width=d * 2, output_height=d * 2)
    img = Image.open(io.BytesIO(png)).convert("RGBA").resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    img.putalpha(mask)
    return img


# ----------------------------------------------------------------------------- faces
def draw_face(d: ImageDraw.ImageDraw, cx, cy, D, mood, t, gaze=(0.0, 0.0)):
    """Cartoon eyes + mouth on top of a flag circle. mood: neutral|happy|shocked|worried|smug."""
    er = D * 0.15
    ey = cy - D * 0.07
    outline = (20, 20, 26)
    blink = (int(t * 10) % 37) == 0  # occasional blink
    for sx in (-1, 1):
        ex = cx + sx * D * 0.18
        r = er * (1.25 if mood == "shocked" else 1.0)
        if blink and mood != "shocked":
            d.line([(ex - r, ey), (ex + r, ey)], fill=outline, width=max(2, int(D * 0.05)))
            continue
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(255, 255, 255), outline=outline,
                  width=max(2, int(D * 0.035)))
        pr = r * (0.38 if mood == "shocked" else 0.5)
        px, py = ex + gaze[0] * r * 0.35, ey + gaze[1] * r * 0.35
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=outline)
        if mood == "smug":  # half-closed lids
            d.rectangle([ex - r - 1, ey - r - 1, ex + r + 1, ey - r * 0.1], fill=outline)
        if mood == "worried":  # slanted brows
            d.line([(ex - r, ey - r * 1.5 - sx * r * 0.3), (ex + r, ey - r * 1.5 + sx * r * 0.3)],
                   fill=outline, width=max(2, int(D * 0.045)))
    my = cy + D * 0.2
    mw = D * 0.22
    lw = max(2, int(D * 0.05))
    if mood == "happy":
        d.arc([cx - mw, my - mw * 0.9, cx + mw, my + mw * 0.6], 20, 160, fill=outline, width=lw)
    elif mood == "smug":
        d.arc([cx - mw * 0.2, my - mw * 0.6, cx + mw * 1.1, my + mw * 0.4], 20, 150, fill=outline, width=lw)
    elif mood == "shocked":
        r = D * 0.085
        d.ellipse([cx - r, my - r, cx + r, my + r * 1.3], fill=outline)
    elif mood == "worried":
        d.arc([cx - mw, my, cx + mw, my + mw * 1.2], 200, 340, fill=outline, width=lw)
        # sweat drop
        sx_, sy_ = cx + D * 0.42, cy - D * 0.3
        s = D * 0.11
        d.polygon([(sx_, sy_ - s * 1.4), (sx_ - s, sy_), (sx_ + s, sy_)], fill=(110, 190, 255))
        d.ellipse([sx_ - s, sy_ - s, sx_ + s, sy_ + s], fill=(110, 190, 255))
    else:
        d.line([(cx - mw * 0.6, my), (cx + mw * 0.6, my)], fill=outline, width=lw)


# ----------------------------------------------------------------------------- captions
LINES = {
    "overtake": [
        ("A", "{A}: excuse me, coming through"),
        ("A", "{A} just passed {B}. Bye!"),
        ("B", "{B}: wait, where did {A} come from?"),
        ("A", "{A}: see you later, {B}"),
        ("B", "{B} did NOT see that coming"),
        ("A", "{A} is on a mission"),
        ("B", "{B}: hey, that was my spot!"),
        ("A", "{A}: nothing personal, {B}"),
        ("A", "{A}: on your left, {B}"),
        ("B", "{B}: I was here first!"),
        ("A", "{A} has entered turbo mode"),
        ("A", "Plot twist: {A} passes {B}"),
        ("B", "{B}: no no no no no"),
        ("B", "{B}: this can't be happening"),
    ],
    "podium": [
        ("A", "BIG MOMENT: {A} passes {B} for #{R}!"),
        ("A", "{A} takes #{R} from {B}!"),
        ("A", "HISTORY: {A} passes {B}"),
        ("A", "{A} is now #{R}. Sorry, {B}!"),
    ],
    "enter": [("A", "{A} has entered the chat"), ("A", "{A}: hello, top {N}!"),
              ("A", "Welcome to the club, {A}"), ("A", "Look who showed up: {A}"),
              ("A", "A wild {A} appears"), ("A", "{A}: did I miss anything?")],
    "exit": [("A", "{A} has left the chat"), ("A", "{A}: I'll be back..."), ("A", "Goodbye, {A}"),
             ("A", "{A}: it was nice while it lasted")],
    "new_leader": [("A", "NEW #1: {A}!"), ("A", "{A} takes the crown")],
    "streak": [("A", "{A}: still #1. Not even trying."), ("A", "{A} is getting comfortable up there"),
               ("A", "Is anyone ever catching {A}?")],
}
PRIORITY = {"new_leader": 6, "podium": 5, "exit": 4, "enter": 3, "overtake": 2, "streak": 1}
SFX_FOR = {"podium": "ding", "new_leader": "ding", "enter": "ding", "exit": "bonk", "overtake": "whoosh", "streak": "pop"}


@dataclass
class Caption:
    speaker: str
    text: str
    start: int
    dur: int


@dataclass
class EntityState:
    mood: str = "neutral"
    mood_until: int = 0
    last_rank: int = 999


# ----------------------------------------------------------------------------- data
@dataclass
class Series:
    years: np.ndarray
    entities: list
    groups: dict
    values: np.ndarray


def load(csv) -> Series:
    df = pd.read_csv(csv)
    if "group" not in df.columns:
        df["group"] = ""
    years = np.array(sorted(df.year.unique()))
    ents = sorted(df.entity.unique())
    groups = df.drop_duplicates("entity").set_index("entity")["group"].astype(str).to_dict()
    pv = df.pivot_table(index="year", columns="entity", values="value").reindex(years).reindex(columns=ents)
    return Series(years, ents, groups, pv.to_numpy(float))


def interpolate(s: Series, step_frames):
    for i in range(len(s.years) - 1):
        v0, v1 = s.values[i], s.values[i + 1]
        for f in range(step_frames):
            t = f / step_frames
            yield s.years[i] + (s.years[i + 1] - s.years[i]) * t, np.where(
                np.isnan(v0), v1, np.where(np.isnan(v1), v0, v0 + (v1 - v0) * t))
    yield float(s.years[-1]), s.values[-1]


def fmt(v, prefix=""):
    return prefix + _fmt(v)


def _fmt(v):
    def trim(x):
        return x.rstrip("0").rstrip(".") if "." in x else x
    a = abs(v)
    if a >= 1e12:
        return trim(f"{v / 1e12:.2f}") + "T"
    if a >= 1e9:
        return trim(f"{v / 1e9:.1f}") + "B" if a < 100e9 else f"{v / 1e9:.0f}B"
    if a >= 1e6:
        return trim(f"{v / 1e6:.1f}") + "M"
    if a >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{v:,.0f}" if a >= 100 else f"{v:.1f}"


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# ----------------------------------------------------------------------------- renderer
class Renderer:
    def __init__(self, s: Series, a):
        self.s, self.a = s, a
        self.top = a.top
        self.rng = random.Random(a.seed)
        self.colors = {e: GROUP_COLORS.get(s.groups.get(e, ""), FALLBACK[i % len(FALLBACK)])
                       for i, e in enumerate(s.entities)}
        self.pos = {e: float(self.top + 2) for e in s.entities}
        if a.vertical:
            self.ct, self.cb = 540, 1720
            self.cl, self.cr = 350, 830
        else:
            self.ct, self.cb = 250, 940
            self.cl, self.cr = 430, 1560
        self.row_h = (self.cb - self.ct) / self.top
        self.bar_h = self.row_h * 0.74
        self.face_d = int(self.bar_h * (0.95 if a.vertical else 1.18))
        self.flags = {}
        self.state = {e: EntityState() for e in s.entities}
        self.captions: list[Caption] = []
        self.used_lines = set()
        self.last_spoke = {}
        self.pair_seen = {}
        self.sfx_events = []  # (frame, name, gain)
        self.prev_order = None
        self.leader_since = 0
        self.ticker = []  # (start_frame, text)
        self.events = []
        if a.events and os.path.exists(a.events):
            ev = pd.read_csv(a.events)
            self.events = sorted(zip(ev.year, ev.text))
        self.fired_events = set()

    def flag(self, e):
        if e not in self.flags:
            self.flags[e] = load_flag(e, self.face_d)
        return self.flags[e]

    # ---------------------------------------------------------------- story detection
    def pick_line(self, kind, A, B="", R=0):
        opts = [o for o in LINES[kind] if (kind, o[1]) not in self.used_lines]
        if not opts and kind in ("podium", "new_leader"):  # big moments always get a caption
            opts = [o for o in LINES[kind] if (kind, o[1]) != getattr(self, "last_tpl", None)]
        if not opts:
            return None, None
        who, tpl = self.rng.choice(opts)
        self.used_lines.add((kind, tpl))
        self.last_tpl = (kind, tpl)
        speaker = A if who == "A" else B
        return speaker, tpl.format(A=short(A), B=short(B), N=self.top, R=R)

    def propose(self, kind, frame, A, B="", R=0):
        if self.a.no_captions:
            return
        pair = frozenset((A, B)) if B else None
        if self.captions and self.captions[-1].start == frame:
            return
        if pair and self.pair_seen.get(pair, -10 ** 9) > frame - self.a.fps * 10:
            return
        # throttle: 1 caption at a time on screen, min gap, entity cooldown
        active = [c for c in self.captions if c.start <= frame < c.start + c.dur]
        if active:
            cur = active[0]
            min_on = 0.8 if kind == "new_leader" else 2.0
            if PRIORITY[kind] <= 3 or frame - cur.start < self.a.fps * min_on:
                return
        elif self.captions and PRIORITY[kind] <= 3 and frame - (self.captions[-1].start + self.captions[-1].dur) < self.a.fps * 1.0:
            return
        if self.last_spoke.get(A, -10 ** 9) > frame - self.a.fps * 4 and kind not in ("new_leader", "exit", "podium"):
            return
        speaker, text = self.pick_line(kind, A, B, R)
        if speaker is None:
            return
        for c in active:  # preempt whatever is on screen for a bigger moment
            c.dur = frame - c.start
        self.captions.append(Caption(speaker, text, frame, int(self.a.fps * 2.4)))
        if pair:
            self.pair_seen[pair] = frame
        self.last_spoke[A] = frame
        self.sfx_events.append((frame, SFX_FOR[kind], 0.9 if kind != "overtake" else 0.7))
        self.sfx_events.append((frame + 2, "pop", 0.5))

    def detect(self, frame, vals):
        order = [self.s.entities[i] for i in np.argsort(-np.nan_to_num(vals, nan=-1))]
        rank = {e: r for r, e in enumerate(order)}
        if self.prev_order is not None:
            prev_rank = {e: r for r, e in enumerate(self.prev_order)}
            for e in order[: self.top + 1]:
                pr, nr = prev_rank[e], rank[e]
                if nr < pr:
                    displaced = self.prev_order[nr]
                    if nr == 0:
                        self.propose("new_leader", frame, e, displaced)
                        self.leader_since = frame
                    elif pr >= self.top > nr:
                        self.propose("enter", frame, e)
                        # whoever fell out
                        out = order[self.top]
                        self.state[out].mood, self.state[out].mood_until = "worried", frame + self.a.fps * 2
                        self.sfx_events.append((frame + int(self.a.fps * 0.9), "bonk", 0.6))
                    elif nr < self.a.podium_ranks:
                        self.propose("podium", frame, e, displaced, R=nr + 1)
                    elif nr < self.top:
                        self.propose("overtake", frame, e, displaced)
                    st = self.state[e]
                    st.mood, st.mood_until = "happy", frame + int(self.a.fps * 1.6)
                    if displaced in self.state and rank[displaced] < self.top + 1:
                        sd = self.state[displaced]
                        sd.mood, sd.mood_until = "shocked", frame + int(self.a.fps * 0.9)
            # leader streak joke every ~4 data steps
            if frame - self.leader_since > self.a.fps * 13:
                self.propose("streak", frame, order[0])
                self.leader_since = frame
        self.prev_order = order
        return rank

    def mood_of(self, e, frame, rank):
        st = self.state[e]
        if frame < st.mood_until:
            return st.mood
        if st.mood == "shocked":  # shocked decays into worried briefly
            st.mood, st.mood_until = "worried", frame + int(self.a.fps * 0.8)
            return "worried"
        if rank.get(e, 99) == 0:
            return "smug"
        return "neutral"

    # ---------------------------------------------------------------- drawing
    def wrap(self, d, text, f, maxw):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def base(self, year, fi=0):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        t = fi / self.a.fps
        show_q = self.a.question and self.a.intro == "overlay" and t < self.a.question_secs
        if self.a.vertical and getattr(self, "hide_header", False):
            self.ticker_y = 420
            return img, d
        if self.a.vertical:
            y = 90
            d.text((60, y), f"{self.a.channel} · Source: {self.a.source}", font=F_SMALL, fill=MUTED)
            y += 50
            for ln in self.wrap(d, self.a.title, F_TITLE, W - 120):
                d.text((60, y), ln, font=F_TITLE, fill=FG)
                y += 76
            sub = self.a.question if show_q else self.a.subtitle
            col = ACCENT if show_q else MUTED
            for ln in self.wrap(d, sub, F_SUB, W - 120):
                d.text((60, y + 6), ln, font=F_SUB, fill=col)
                y += 44
            self.ticker_y = y + 24
            return img, d
        d.text((80, 56), self.a.title, font=F_TITLE, fill=FG)
        if show_q:
            d.text((80, 136), self.a.question, font=F_SUB, fill=ACCENT)
        else:
            d.text((80, 136), self.a.subtitle, font=F_SUB, fill=MUTED)
        self.ticker_y = 132
        groups = sorted({g for g in self.s.groups.values() if g})
        x = 80
        for g in groups:
            d.rounded_rectangle([x, H - 88, x + 26, H - 62], radius=6, fill=GROUP_COLORS.get(g, MUTED))
            d.text((x + 38, H - 90), g, font=F_LEGEND, fill=MUTED)
            x += 38 + d.textlength(g, font=F_LEGEND) + 44
        foot = f"Source: {self.a.source}"
        d.text((W - 80 - d.textlength(foot, font=F_SMALL), H - 80), foot, font=F_SMALL, fill=MUTED)
        d.text((W - 80 - d.textlength(self.a.channel, font=F_SMALL), 60), self.a.channel, font=F_SMALL, fill=MUTED)
        return img, d

    def draw_bubble(self, img, x, y, text, k, align_left=True):
        """k in [0,1+] animation progress; draws a speech bubble whose tail points left at (x, y)."""
        d = ImageDraw.Draw(img)
        tw = d.textlength(text, font=F_BUBBLE)
        pad_x, h = 22, 58
        bw = tw + pad_x * 2
        sc = max(0.0, ease_out_back(min(1.0, k)))
        if sc <= 0.01:
            return
        layer = Image.new("RGBA", (int(bw) + 40, h + 20), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([18, 6, 18 + bw, 6 + h], radius=18, fill=BUBBLE + (255,))
        ld.polygon([(2, 6 + h / 2), (22, 6 + h / 2 - 12), (22, 6 + h / 2 + 12)], fill=BUBBLE + (255,))
        ld.text((18 + pad_x, 6 + (h - 38) / 2), text, font=F_BUBBLE, fill=BUBBLE_TXT)
        if sc != 1.0:
            nw, nh = max(1, int(layer.width * sc)), max(1, int(layer.height * sc))
            layer = layer.resize((nw, nh), Image.LANCZOS)
        if x + layer.width > W - 30 and not self.a.vertical:  # no room right of the bar: drop below the row
            x = W - 30 - layer.width
            y = y + self.row_h * 0.95
        img.paste(layer, (int(x), int(y - layer.height / 2)), layer)

    def frame(self, fi, year, vals, alpha=1.0, show_year=True, rank_vals=None):
        img, d = self.base(year, fi)
        rank = self.detect(fi, vals if rank_vals is None else rank_vals)
        order = sorted(rank, key=rank.get)
        for e in self.s.entities:
            tgt = rank[e] if rank[e] < self.top else self.top + 1.5
            self.pos[e] += (tgt - self.pos[e]) * self.a.ease
        top_vals = [vals[self.s.entities.index(e)] for e in order[: self.top]]
        vmax = max(max(top_vals), 1e-9)
        scale = (self.cr - self.cl) / (vmax * 1.05)
        # grid
        nice = 10 ** math.floor(math.log10(vmax))
        step = nice if vmax / nice >= 4 else nice / 2
        while step * scale < (150 if self.a.vertical else 110):
            step *= 2
        v = step
        while v < vmax * 1.05:
            x = self.cl + v * scale
            d.line([(x, self.ct - 10), (x, self.cb)], fill=GRID, width=2)
            lbl = fmt(v, self.a.prefix)
            d.text((x - d.textlength(lbl, font=F_SMALL) / 2, self.ct - 44), lbl, font=F_SMALL, fill=MUTED)
            v += step
        # big year
        if show_year:
            yt = f"{int(year)}"
            d.text((W - 90 - d.textlength(yt, font=F_YEAR), H - 330), yt, font=F_YEAR, fill=(62, 66, 82))
        bar_end = {}
        for e in sorted(self.s.entities, key=lambda k: -self.pos[k]):
            if self.pos[e] > self.top + 0.6:
                continue
            val = vals[self.s.entities.index(e)]
            if np.isnan(val) or val <= 0:
                continue
            y = self.ct + self.pos[e] * self.row_h
            cy = y + self.bar_h / 2
            x1 = self.cl + val * scale
            fade = 1.0 if self.pos[e] < self.top - 0.5 else max(0.0, self.top + 0.6 - self.pos[e])
            mixc = lambda c: tuple(int(BG[i] + (c[i] - BG[i]) * fade) for i in range(3))
            tgt_e = rank[e] if rank[e] < self.top else self.top + 1.5
            tfade = fade * max(0.0, min(1.0, 1 - (abs(self.pos[e] - tgt_e) - 0.08) * 3.2))
            mixt = lambda c: tuple(int(BG[i] + (c[i] - BG[i]) * tfade) for i in range(3))
            d.rounded_rectangle([self.cl, y, max(self.cl + self.bar_h, x1), y + self.bar_h],
                                radius=int(self.bar_h / 2), fill=mixc(self.colors[e]))
            rx, nx, nmax = (20, 66, self.cl - 80) if self.a.vertical else (self.cl - 400, self.cl - 355, 330)
            if rank[e] < self.top:
                d.text((rx, self.ct + rank[e] * self.row_h + self.bar_h / 2 - F_RANK.size * 0.6), f"{rank[e] + 1}", font=F_RANK, fill=MUTED)
            nm = short(e)
            while d.textlength(nm, font=F_LABEL) > nmax and len(nm) > 4:
                nm = nm[:-2].rstrip() + "…" if not nm.endswith("…") else nm[:-2] + "…"
            if rank[e] < self.top:  # names snap to their target slot, so two names never overlap
                cys = self.ct + rank[e] * self.row_h + self.bar_h / 2
                d.text((nx, cys - F_LABEL.size * 0.62), nm, font=F_LABEL, fill=FG)
            # face at the bar tip
            fx = max(self.cl + self.bar_h, x1) - self.face_d * 0.55
            fy = cy - self.face_d / 2
            fl = self.flag(e)
            if fade > 0.6:
                if fl is not None:
                    img.paste(fl, (int(fx), int(fy)), fl)
                else:
                    d.ellipse([fx, fy, fx + self.face_d, fy + self.face_d], fill=self.colors[e])
                d.ellipse([fx, fy, fx + self.face_d, fy + self.face_d], outline=(20, 20, 26), width=3)
                mood = self.mood_of(e, fi, rank)
                gaze = (0.0, -1.0) if mood == "happy" else (0.6, 0.0)
                draw_face(d, fx + self.face_d / 2, cy, self.face_d, mood, fi / self.a.fps, gaze)
            vx = fx + self.face_d + 14
            vtxt = fmt(val, self.a.prefix) + (f" {self.a.unit}" if self.a.unit else "")
            d.text((vx, cy - F_VALUE.size * 0.6), vtxt, font=F_VALUE, fill=mixt(FG))
            bar_end[e] = (vx + d.textlength(vtxt, font=F_VALUE) + 18, cy)
        # captions
        for c in self.captions:
            if c.start <= fi < c.start + c.dur and c.speaker in bar_end:
                k = (fi - c.start) / (self.a.fps * 0.28)
                out = (c.start + c.dur - fi) / (self.a.fps * 0.25)
                x, y = bar_end[c.speaker]
                if self.a.vertical:  # fixed caption band between header and chart
                    x, y = 40, self.ct - 95
                self.draw_bubble(img, x, y, c.text, min(k, out))
        # history ticker
        for yr, text in self.events:
            if year >= yr and yr not in self.fired_events:
                self.fired_events.add(yr)
                self.ticker.append((fi, f"{yr} · {text}"))
                self.sfx_events.append((fi, "pop", 0.6))
        for start, text in self.ticker:
            age = (fi - start) / self.a.fps
            if 0 <= age < 2.4:
                d2 = ImageDraw.Draw(img)
                tw = d2.textlength(text, font=F_TICK)
                a_ = min(1.0, age / 0.25, (2.4 - age) / 0.3)
                xr = W - 60 if self.a.vertical else W - 80
                y0 = self.ticker_y
                col = tuple(int(BG[i] + (ACCENT[i] - BG[i]) * a_) for i in range(3))
                d2.rounded_rectangle([xr - tw - 40, y0, xr, y0 + 54], radius=27, outline=col, width=3)
                d2.text((xr - tw - 20, y0 + 9), text, font=F_TICK, fill=col)
        if alpha < 1:
            img = Image.blend(Image.new("RGB", (W, H), BG), img, alpha)
        return img

    def card(self, lines, k):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        a = min(1.0, k * 2.5)
        y = H / 2 - 120
        for text, f, col in lines:
            c = tuple(int(BG[i] + (col[i] - BG[i]) * a) for i in range(3))
            tw = d.textlength(text, font=f)
            d.text(((W - tw) / 2, y), text, font=f, fill=c)
            y += f.size + 34
        return img

def overlay_text_block(img, lines, k, box=True, cy=None, cx=None, maxw_=None):
    """lines: [(text, font, color)]; centered block with dark plate; k = opacity 0..1"""
    if k <= 0.01:
        return img
    d0 = ImageDraw.Draw(img)
    widths, heights = [], []
    wrapped = []
    for text, f, col in lines:
        words, cur, out = text.split(), "", []
        for w_ in words:
            t = (cur + " " + w_).strip()
            if d0.textlength(t, font=f) <= (maxw_ or W - 140) or not cur:
                cur = t
            else:
                out.append(cur); cur = w_
        if cur:
            out.append(cur)
        for ln in out:
            wrapped.append((ln, f, col))
    total = sum(f.size * 1.18 for _, f, _ in wrapped)
    maxw = max(d0.textlength(t, font=f) for t, f, _ in wrapped)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    cx = W / 2 if cx is None else cx
    y = (H * 0.42 if cy is None else cy) - total / 2
    if box:
        ld.rounded_rectangle([cx - maxw / 2 - 50, y - 40, cx + maxw / 2 + 50, y + total + 30], radius=36,
                             fill=(10, 11, 16, int(235 * k)))
    for t, f, col in wrapped:
        tw = ld.textlength(t, font=f)
        ld.text((cx - tw / 2, y), t, font=f, fill=col + (int(255 * k),))
        y += f.size * 1.18
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")


def stack_scene(r, a, last, final_rank, fi0):
    """#1 as one column vs the next N stacked into one column; segments drop in one by one."""
    s, fps = r.s, a.fps
    year, vals = last
    lead = s.entities[final_rank[0]]
    rest = [s.entities[k] for k in final_rank[1:1 + a.stack]]
    v = lambda e: float(vals[s.entities.index(e)])
    lv, tot = v(lead), sum(v(e) for e in rest)
    vert = a.vertical
    base_y = 1480 if vert else 850
    maxh = 880 if vert else 620
    colw = 300 if vert else 290
    xl = (W / 2 - colw - 70) if vert else 260
    xr = (W / 2 + 70) if vert else 260 + colw + 130
    sc = maxh / max(lv, tot)
    F_BIG, F_MID, F_SM = font(96 if vert else 84, "Black"), font(58 if vert else 50, "Bold"), font(40 if vert else 34, "SemiBold")
    lines = [t for t in (a.reveal_text.split("|") if a.reveal_text else [])]
    n = int(fps * a.stack_secs)
    t_drop0, t_gap = 0.7, 0.22
    t_text = t_drop0 + t_gap * len(rest) + 0.3
    r.sfx_events.append((fi0, "whoosh", 0.8))
    for j in range(len(rest)):
        r.sfx_events.append((fi0 + int((t_drop0 + t_gap * j + 0.2) * fps), "pop", 0.8))
    r.sfx_events.append((fi0 + int(t_text * fps), "fanfare", 0.9))
    for i in range(n):
        t = i / fps
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # header: year
        d.text((60 if vert else 80, 90 if vert else 56), f"{a.title} · {int(year)}", font=F_SM, fill=MUTED)
        # lead column grows
        g = min(1.0, t / 0.6)
        g = 1 - (1 - g) ** 3
        h = lv * sc * g
        d.rounded_rectangle([xl, base_y - h, xl + colw, base_y], radius=18, fill=r.colors[lead])
        fl = load_flag(lead, 120 if vert else 96)
        if fl is not None:
            fx = int(xl + colw / 2 - fl.width / 2)
            img.paste(fl, (fx, int(base_y + 20)), fl)
        nm = short(lead)
        d.text((xl + colw / 2 - d.textlength(nm, font=F_MID) / 2, base_y + (150 if vert else 120)), nm, font=F_MID, fill=FG)
        lt = fmt(lv * g, a.prefix)
        d.text((xl + colw / 2 - d.textlength(lt, font=F_MID) / 2, base_y - h - 74), lt, font=F_MID, fill=FG)
        # dashed line at the lead's height
        if g >= 1:
            yy = base_y - lv * sc
            for xx in range(int(xl), int(xr), 28):
                d.line([(xx, yy), (xx + 14, yy)], fill=(255, 255, 255), width=3)
        # stacked column: segments drop in from above
        y = base_y
        shown = 0.0
        for j, e in enumerate(rest):
            tj = t - (t_drop0 + t_gap * j)
            if tj < 0:
                break
            k = min(1.0, tj / 0.25)
            sh = v(e) * sc
            off = (1 - (1 - (1 - k) ** 2)) * 300
            top_ = y - sh - off
            d.rounded_rectangle([xr, top_, xr + colw, y - off - 3], radius=10, fill=r.colors[e])
            if sh > 46:
                fd = int(min(sh - 10, 70 if vert else 56))
                f2 = load_flag(e, fd)
                if f2 is not None:
                    img.paste(f2, (int(xr + 12), int(top_ + (sh - fd) / 2)), f2)
            lbl = short(e)
            if sh > 46 and d.textlength(lbl, font=F_SM) < colw - (fd if sh > 46 else 0) - 30:
                d.text((xr + fd + 24, top_ + sh / 2 - F_SM.size * 0.6), lbl, font=F_SM, fill=(15, 16, 20))
            else:  # thin or long-named segment: label outside, right of the column
                F_T = font(30 if vert else 26, "SemiBold")
                lbl = "Saudi" if lbl == "Saudi Arabia" else lbl
                d.text((xr + colw + 14, top_ + sh / 2 - F_T.size * 0.6), lbl, font=F_T, fill=FG)
            y -= sh
            shown += v(e) * (1 if k >= 1 else k)
        if t >= t_drop0 + t_gap * len(rest) + 0.3:
            tt = fmt(shown, a.prefix)
            d.text((xr + colw / 2 - d.textlength(tt, font=F_MID) / 2, y - 74), tt, font=F_MID,
                   fill=(255, 209, 64) if shown > lv else FG)
        lab = a.stack_label or f"Next {len(rest)}"
        d.text((xr + colw / 2 - d.textlength(lab, font=F_MID) / 2, base_y + (150 if vert else 120)), lab, font=F_MID, fill=FG)
        d.text((xr + colw / 2 - d.textlength("combined", font=F_SM) / 2, base_y + (220 if vert else 180)), "combined", font=F_SM, fill=MUTED)
        img_out = img
        if t >= t_text and lines:
            k = min(1.0, (t - t_text) / 0.25)
            F_R1 = font(54 if vert else 46, "Bold")
            tl = [(ln, F_BIG if j == 1 else F_R1, (255, 209, 64) if j == 1 else (235, 235, 240)) for j, ln in enumerate(lines)]
            img_out = overlay_text_block(img, tl, k, box=False, cy=(300 if vert else 430), cx=(W / 2 if vert else W * 0.75),
                                         maxw_=(W - 120 if vert else 760))
        if t >= t_text + 0.6 and a.cta:
            k = min(1.0, (t - t_text - 0.6) / 0.25)
            img_out = overlay_text_block(img_out, [(a.cta, F_MID, ACCENT)], k, box=False,
                                         cy=(1830 if vert else 640), cx=(W / 2 if vert else W * 0.75),
                                         maxw_=(W - 120 if vert else 760))
        yield img_out
    return


def endcard(a, t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f1 = font(64, "Bold")
    k = min(1.0, t / 0.4)
    col = tuple(int(BG[i] + (FG[i] - BG[i]) * k) for i in range(3))
    tw = d.textlength(a.endcard_text, font=f1)
    d.text(((W - tw) / 2, 110), a.endcard_text, font=f1, fill=col)
    d.text(((W - d.textlength(a.channel, font=F_SUB)) / 2, H - 120), a.channel, font=F_SUB, fill=MUTED)
    return img


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--unit", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--channel", default="Numbers in Motion")
    ap.add_argument("--question", default="", help="intro question, answered at the end")
    ap.add_argument("--events", default="")
    ap.add_argument("--out", default="out/video_v2.mp4")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds-per-step", type=float, default=2.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--vertical", action="store_true", help="1080x1920 Shorts layout")
    ap.add_argument("--intro", choices=["card", "overlay"], default="overlay")
    ap.add_argument("--question-secs", type=float, default=4.0)
    ap.add_argument("--outro", type=float, default=4.0)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--start-year", type=float, default=None, help="skip frames before this year")
    ap.add_argument("--hook", default="", help="Shorts v2: huge centered question over the race for the first seconds")
    ap.add_argument("--hook-secs", type=float, default=2.2)
    ap.add_argument("--reveal", action="store_true", help="Shorts v2: big '#1 is ...' reveal + comment CTA outro")
    ap.add_argument("--cta", default="Comment your country ↓")
    ap.add_argument("--reveal-text", default="", help="custom reveal lines separated by | (2nd line is the big one)")
    ap.add_argument("--podium-ranks", type=int, default=3, help="overtakes into these top ranks count as big moments")
    ap.add_argument("--no-captions", action="store_true", help="no speech bubbles")
    ap.add_argument("--snap-ranks", action="store_true", help="rows reorder once per data step, not every frame")
    ap.add_argument("--ease", type=float, default=0.18, help="row movement speed per frame (0.18 smooth, 0.35 snappy)")
    ap.add_argument("--hook-size", type=int, default=0)
    ap.add_argument("--stack", type=int, default=0, help="outro: #1 vs the next N combined, stacked columns")
    ap.add_argument("--stack-label", default="", help="label for the stacked column (default 'Next N')")
    ap.add_argument("--stack-secs", type=float, default=6.0)
    ap.add_argument("--endcard", type=float, default=0.0, help="seconds of clean end-screen hold (long videos)")
    ap.add_argument("--endcard-text", default="Which race should we do next? ↓")
    a = ap.parse_args()
    global W, H, F_LABEL, F_VALUE, F_RANK
    if a.vertical:
        W, H = 1080, 1920
        F_LABEL, F_VALUE, F_RANK = font(44, "SemiBold"), font(40, "Medium"), font(36, "Medium")

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    s = load(a.csv)
    r = Renderer(s, a)
    fps = a.fps
    step_frames = int(a.seconds_per_step * fps)
    silent = a.out.replace(".mp4", "_silent.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset",
                           "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    fi = 0

    def push(img):
        nonlocal fi
        ff.stdin.write(img.tobytes())
        fi += 1

    # intro: question card
    if a.question and a.intro == "card":
        n = int(fps * 2.6)
        for i in range(n):
            push(r.card([(a.question, F_Q, FG), ("Guess in the comments before it ends ↓", F_Q2, ACCENT)], i / n))
        r.sfx_events.append((2, "pop", 0.7))
    elif a.intro == "card":
        n = int(fps * 1.5)
        for i in range(n):
            push(r.card([(a.title, F_Q, FG), (a.subtitle, F_Q2, MUTED)], i / n))
    r.sfx_events.append((fi, "whoosh", 0.8))
    frames = list(interpolate(s, step_frames))
    if a.start_year is not None:
        frames = [f_ for f_ in frames if f_[0] >= a.start_year]
        r.fired_events.update(yr for yr, _ in r.events if yr < a.start_year)
        v0 = frames[0][1]
        order0 = sorted(range(len(s.entities)), key=lambda k: -np.nan_to_num(v0[k], nan=-1))
        for rk, k in enumerate(order0):
            r.pos[s.entities[k]] = rk if rk < r.top else r.top + 1.5
    hs = a.hook_size or (104 if a.vertical else 96)
    F_HOOK = font(hs, "Black") if os.path.exists(os.path.join(FONT_DIR, "Inter-Black.otf")) else font(hs, "Bold")
    # vertical: hook sits in the header band above the chart; horizontal: in the empty lower-right area
    hook_pos = dict(cy=290, cx=W / 2, maxw_=W - 120) if a.vertical else dict(cy=H * 0.46, cx=W * 0.62, maxw_=980)
    last = None
    keyvals = {}
    for y_, v_ in frames:
        if abs(y_ - round(y_)) < 1e-6 and int(round(y_)) in {int(x) for x in s.years}:
            keyvals.setdefault(round(y_), v_)
    keys = sorted(keyvals)
    for i, (year, vals) in enumerate(frames):
        r.hide_header = bool(a.hook) and i / fps < a.hook_secs - 0.2
        rv = None
        if a.snap_ranks:  # reorder once per data step: rank by the upcoming keyframe
            nxt = min((k for k in keys if k >= year - 1e-6), default=keys[-1])
            rv = keyvals[nxt]
        img = r.frame(fi, year, vals, alpha=1.0 if a.hook else min(1.0, i / (fps * 0.5)), rank_vals=rv)
        if a.hook:
            t_ = i / fps
            k = 1.0 if t_ < a.hook_secs - 0.35 else max(0.0, (a.hook_secs - t_) / 0.35)
            r.hide_header = t_ < a.hook_secs - 0.2
            if k > 0:
                img = overlay_text_block(img, [(a.hook, F_HOOK, (255, 209, 64))], k, **hook_pos)
        push(img)
        last = (year, vals)
        if i % (fps * 5) == 0:
            print(f"  {i}/{len(frames)} year={year:.1f}", flush=True)
    # outro: hold final frame with reveal
    final_rank = sorted(range(len(s.entities)), key=lambda k: -np.nan_to_num(last[1][k], nan=-1))
    if not a.stack:
        r.sfx_events.append((fi, "fanfare", 0.8))
    reveal = "Did you guess right? Tell us below ↓"
    if a.stack:
        for img in stack_scene(r, a, last, final_rank, fi):
            push(img)
        a.outro = 0
        a.reveal = False
    if a.endcard:
        for i in range(int(fps * a.endcard)):
            push(endcard(a, i / fps))
        a.outro = 0
    if a.reveal:
        top1 = s.entities[final_rank[0]]
        F_R1, F_R2 = font(64, "Bold"), font(120, "Bold")
        for i in range(int(fps * a.outro)):
            img = r.frame(fi, *last)
            k = min(1.0, i / (fps * 0.25))
            if a.reveal_text:
                parts = a.reveal_text.split("|")
                lines = [(t_, F_R2 if j == 1 else F_R1, (255, 209, 64) if j == 1 else (230, 230, 235))
                         for j, t_ in enumerate(parts)]
            else:
                lines = [(f"#1 in {int(last[0])}:", F_R1, (230, 230, 235)),
                         (short(top1).upper(), F_R2, (255, 209, 64))]
            if a.vertical:  # keep the final ranking visible: text goes in the header band
                r.hide_header = True
                img = r.frame(fi, *last)
                lines = [(t_, font(110, "Black") if f_ is F_R2 else font(56, "Bold"), c_) for t_, f_, c_ in lines]
                img = overlay_text_block(img, lines, k, cy=270, maxw_=W - 100)
                img = overlay_text_block(img, [(a.cta, font(54, "Bold"), (255, 209, 64))], k, box=False, cy=1810, maxw_=W - 100)
            else:
                img = overlay_text_block(img, lines + [(a.cta, F_R1, (230, 230, 235))], k)
            push(img)
        a.outro = 0
    for i in range(int(fps * a.outro)):
        img = r.frame(fi, *last)
        d = ImageDraw.Draw(img)
        k = min(1.0, i / (fps * 0.3))
        tw = d.textlength(reveal, font=F_TICK)
        xr, y0 = (W - 60 if a.vertical else W - 80), r.ticker_y
        d.rounded_rectangle([xr - tw - 40, y0, xr, y0 + 54], radius=27, fill=ACCENT if k >= 1 else BG)
        d.text((xr - tw - 20, y0 + 9), reveal, font=F_TICK, fill=BG if k >= 1 else ACCENT)
        push(img)
    ff.stdin.close()
    ff.wait()
    duration = fi / fps
    print(f"video frames={fi} ({duration:.1f}s), captions={len(r.captions)}")
    for c in r.captions:
        print(f"   {c.start / fps:5.1f}s  {c.speaker:15s} {c.text}")

    if a.no_audio:
        os.replace(silent, a.out)
        return
    wav = a.out.replace(".mp4", ".wav")
    audio.write_wav(wav, audio.mix(duration, [(f / fps, n, g) for f, n, g in r.sfx_events]))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    os.remove(silent)
    os.remove(wav)
    print("->", a.out)


if __name__ == "__main__":
    main()
