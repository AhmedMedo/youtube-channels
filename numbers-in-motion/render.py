"""Racing bar chart video renderer (faceless data-viz pipeline).

Input : tidy CSV with columns  entity, group, year, value
Output: 1080p MP4 (H.264) + thumbnail PNG

Usage:
    python render.py --csv data/population.csv --title "Most Populous Countries" \
        --subtitle "1952 - 2007" --unit "people" --out out/population.mp4 \
        --top 10 --seconds-per-step 2 --fps 30

Everything is drawn with Pillow and piped as raw frames into ffmpeg, so there is no
dependency on matplotlib animation and rendering stays fast and fully controllable.
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------- theme
W, H = 1920, 1080
BG = (14, 16, 22)
FG = (240, 240, 245)
MUTED = (140, 145, 160)
GRID = (40, 44, 56)
ACCENT = (255, 196, 61)

GROUP_COLORS = {
    "Asia": (255, 111, 97),
    "Europe": (91, 155, 255),
    "Africa": (255, 196, 61),
    "Americas": (87, 212, 148),
    "Oceania": (196, 132, 255),
}
FALLBACK_COLORS = [
    (255, 111, 97), (91, 155, 255), (255, 196, 61), (87, 212, 148),
    (196, 132, 255), (255, 159, 67), (73, 203, 227), (241, 109, 196),
]

FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(size: int, weight: str = "SemiBold") -> ImageFont.FreeTypeFont:
    path = os.path.join(FONT_DIR, f"Inter-{weight}.otf")
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, "Inter-Regular.otf")
    return ImageFont.truetype(path, size)


F_TITLE = font(64, "Bold")
F_SUB = font(34, "Medium")
F_YEAR = font(190, "Bold")
F_LABEL = font(40, "SemiBold")
F_VALUE = font(36, "Medium")
F_RANK = font(30, "Medium")
F_SMALL = font(26, "Regular")
F_LEGEND = font(28, "Medium")


# ----------------------------------------------------------------------------- helpers
def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def fmt_value(v: float, unit: str) -> str:
    if unit.startswith("$"):
        prefix, unit = "$", ""
    else:
        prefix = ""
    a = abs(v)
    def trim(x: str) -> str:
        return x.rstrip("0").rstrip(".") if "." in x else x
    if a >= 1e9:
        s = trim(f"{v / 1e9:.2f}") + "B"
    elif a >= 1e6:
        s = trim(f"{v / 1e6:.1f}") + "M"
    elif a >= 1e3:
        s = f"{v / 1e3:.0f}K"
    else:
        s = f"{v:,.0f}" if a >= 100 else f"{v:.1f}"
    return f"{prefix}{s}{(' ' + unit) if unit else ''}"


def rounded_bar(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, color, radius=14):
    if x1 - x0 < 2:
        return
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=color)


# ----------------------------------------------------------------------------- data
@dataclass
class Series:
    years: np.ndarray                 # sorted distinct years
    entities: list[str]
    groups: dict[str, str]
    values: np.ndarray                # shape (n_years, n_entities), NaN allowed


def load(csv: str) -> Series:
    df = pd.read_csv(csv)
    need = {"entity", "year", "value"}
    if not need.issubset(df.columns):
        sys.exit(f"CSV must have columns {need}, got {list(df.columns)}")
    if "group" not in df.columns:
        df["group"] = ""
    years = np.array(sorted(df.year.unique()))
    entities = sorted(df.entity.unique())
    groups = df.drop_duplicates("entity").set_index("entity")["group"].astype(str).to_dict()
    pivot = df.pivot_table(index="year", columns="entity", values="value").reindex(years)
    pivot = pivot.reindex(columns=entities)
    return Series(years, entities, groups, pivot.to_numpy(dtype=float))


def interpolate(series: Series, step_frames: int):
    """Yield (year_float, values_vector) for every frame, linearly interpolating values."""
    for i in range(len(series.years) - 1):
        y0, y1 = series.years[i], series.years[i + 1]
        v0, v1 = series.values[i], series.values[i + 1]
        for f in range(step_frames):
            t = f / step_frames
            vals = np.where(np.isnan(v0), v1, np.where(np.isnan(v1), v0, v0 + (v1 - v0) * t))
            yield y0 + (y1 - y0) * t, vals
    yield float(series.years[-1]), series.values[-1]


# ----------------------------------------------------------------------------- drawing
class Renderer:
    def __init__(self, series: Series, title: str, subtitle: str, unit: str, top: int,
                 source: str, channel: str):
        self.s = series
        self.title, self.subtitle, self.unit = title, subtitle, unit
        self.top, self.source, self.channel = top, source, channel
        self.colors = {}
        for i, e in enumerate(series.entities):
            g = series.groups.get(e, "")
            self.colors[e] = GROUP_COLORS.get(g, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        # smooth rank positions: current y position per entity (in rank units)
        self.pos = {e: float(top + 2) for e in series.entities}
        self.chart_top, self.chart_bottom = 230, 940
        self.chart_left, self.chart_right = 420, 1700
        self.row_h = (self.chart_bottom - self.chart_top) / top

    def _frame_base(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((80, 60), self.title, font=F_TITLE, fill=FG)
        d.text((80, 140), self.subtitle, font=F_SUB, fill=MUTED)
        # legend (groups)
        groups = sorted({g for g in self.s.groups.values() if g})
        x = 80
        for g in groups:
            c = GROUP_COLORS.get(g, MUTED)
            d.rounded_rectangle([x, 992, x + 26, 1018], radius=6, fill=c)
            d.text((x + 38, 990), g, font=F_LEGEND, fill=MUTED)
            x += 38 + d.textlength(g, font=F_LEGEND) + 44
        foot = f"Source: {self.source}" if self.source else ""
        if foot:
            d.text((W - 80 - d.textlength(foot, font=F_SMALL), 1000), foot, font=F_SMALL, fill=MUTED)
        if self.channel:
            d.text((W - 80 - d.textlength(self.channel, font=F_SMALL), 60), self.channel,
                   font=F_SMALL, fill=MUTED)
        return img, d

    def frame(self, year: float, vals: np.ndarray, alpha: float = 1.0, show_year: bool = True) -> Image.Image:
        img, d = self._frame_base()
        order = np.argsort(-np.nan_to_num(vals, nan=-1))
        ranked = [self.s.entities[i] for i in order[: self.top]]
        target = {e: r for r, e in enumerate(ranked)}
        # ease every entity toward its target rank (entities out of top drift below)
        for e in self.s.entities:
            tgt = target.get(e, self.top + 1.5)
            self.pos[e] += (tgt - self.pos[e]) * 0.18
        vmax = max(float(np.nanmax(vals[order[: self.top]])), 1e-9)
        scale = (self.chart_right - self.chart_left) / (vmax * 1.08)

        # grid lines
        nice = 10 ** math.floor(math.log10(vmax))
        step = nice if vmax / nice >= 4 else nice / 2
        v = step
        while v < vmax * 1.08:
            x = self.chart_left + v * scale
            d.line([(x, self.chart_top - 10), (x, self.chart_bottom)], fill=GRID, width=2)
            lbl = fmt_value(v, "")
            d.text((x - d.textlength(lbl, font=F_SMALL) / 2, self.chart_top - 44), lbl,
                   font=F_SMALL, fill=MUTED)
            v += step

        # bars (draw lower ranks first so the leaders overlap on top when crossing)
        for e in sorted(self.s.entities, key=lambda k: -self.pos[k]):
            if self.pos[e] > self.top + 0.6:
                continue
            idx = self.s.entities.index(e)
            val = vals[idx]
            if np.isnan(val) or val <= 0:
                continue
            y = self.chart_top + self.pos[e] * self.row_h
            bar_h = self.row_h * 0.72
            x1 = self.chart_left + val * scale
            fade = 1.0 if self.pos[e] < self.top - 0.5 else max(0.0, (self.top + 0.6 - self.pos[e]))
            c = tuple(int(BG[i] + (self.colors[e][i] - BG[i]) * fade) for i in range(3))
            rounded_bar(d, self.chart_left, y, x1, y + bar_h, c)
            tc = tuple(int(BG[i] + (FG[i] - BG[i]) * fade) for i in range(3))
            mc = tuple(int(BG[i] + (MUTED[i] - BG[i]) * fade) for i in range(3))
            # rank + name on the left
            rank_txt = f"{int(round(self.pos[e])) + 1}"
            d.text((self.chart_left - 390, y + bar_h / 2 - 20), rank_txt, font=F_RANK, fill=mc)
            name = e if d.textlength(e, font=F_LABEL) < 320 else e[:16] + "…"
            d.text((self.chart_left - 340, y + bar_h / 2 - 24), name, font=F_LABEL, fill=tc)
            # value on the right of bar
            d.text((x1 + 18, y + bar_h / 2 - 22), fmt_value(val, self.unit), font=F_VALUE, fill=tc)

        # big year
        ytxt = f"{int(year)}"
        if show_year:
          d.text((W - 90 - d.textlength(ytxt, font=F_YEAR), H - 330), ytxt, font=F_YEAR,
               fill=(70, 74, 90))
        if alpha < 1.0:
            overlay = Image.new("RGB", (W, H), BG)
            img = Image.blend(overlay, img, alpha)
        return img

    def title_card(self, progress: float) -> Image.Image:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        a = ease_in_out(min(1.0, progress * 2))
        c = tuple(int(BG[i] + (FG[i] - BG[i]) * a) for i in range(3))
        m = tuple(int(BG[i] + (MUTED[i] - BG[i]) * a) for i in range(3))
        t_w = d.textlength(self.title, font=F_TITLE)
        d.text(((W - t_w) / 2, H / 2 - 90), self.title, font=F_TITLE, fill=c)
        s_w = d.textlength(self.subtitle, font=F_SUB)
        d.text(((W - s_w) / 2, H / 2 + 0), self.subtitle, font=F_SUB, fill=m)
        d.rounded_rectangle([W / 2 - 60 * a, H / 2 + 70, W / 2 + 60 * a, H / 2 + 76], radius=3,
                            fill=tuple(int(BG[i] + (ACCENT[i] - BG[i]) * a) for i in range(3)))
        return img

    def thumbnail(self, year: float, vals: np.ndarray, headline: str, path: str):
        """Thumbnail = final frame, cropped/zoomed, with a huge headline."""
        self.pos = {e: float(self.top + 2) for e in self.s.entities}
        for _ in range(40):  # settle positions
            img = self.frame(year, vals, show_year=False)
        img = img.resize((1280, 720), Image.LANCZOS)
        d = ImageDraw.Draw(img)
        big = font(88, "Bold")
        lines = headline.split("\n")
        y = 250
        for ln in lines:
            w = d.textlength(ln, font=big)
            x = 1250 - w
            d.rounded_rectangle([x - 20, y - 6, x + w + 20, y + 98], radius=14, fill=(0, 0, 0))
            d.text((x, y), ln, font=big, fill=ACCENT)
            y += 110
        img.save(path, quality=92)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--unit", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--channel", default="")
    ap.add_argument("--out", default="out/video.mp4")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds-per-step", type=float, default=2.0,
                    help="seconds between two consecutive years in the data")
    ap.add_argument("--intro", type=float, default=2.5)
    ap.add_argument("--outro", type=float, default=3.0)
    ap.add_argument("--music", default="", help="optional audio file to mux (looped/trimmed)")
    ap.add_argument("--thumb-text", default="")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    s = load(args.csv)
    r = Renderer(s, args.title, args.subtitle, args.unit, args.top, args.source, args.channel)
    step_frames = max(1, int(args.seconds_per_step * args.fps))

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(args.fps), "-i", "-"]
    if args.music:
        cmd += ["-stream_loop", "-1", "-i", args.music, "-shortest", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def push(img: Image.Image):
        proc.stdin.write(img.tobytes())

    n_intro = int(args.intro * args.fps)
    for f in range(n_intro):
        push(r.title_card(f / n_intro))

    frames = list(interpolate(s, step_frames))
    total = len(frames)
    last = None
    for i, (year, vals) in enumerate(frames):
        alpha = min(1.0, i / (args.fps * 0.6))  # fade in from title card
        img = r.frame(year, vals, alpha)
        push(img)
        last = (year, vals)
        if i % (args.fps * 5) == 0:
            print(f"  {i}/{total} frames  year={year:.1f}", flush=True)

    for _ in range(int(args.outro * args.fps)):
        push(r.frame(*last))

    proc.stdin.close()
    proc.wait()
    print(f"video -> {args.out}")

    if args.thumb_text and last:
        thumb = os.path.splitext(args.out)[0] + "_thumb.jpg"
        r.thumbnail(last[0], last[1], args.thumb_text, thumb)
        print(f"thumbnail -> {thumb}")


if __name__ == "__main__":
    main()
