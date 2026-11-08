"""Sleep channel — brand candidates. Generates logo (800x800), circle preview, banner (2560x1440,
safe area 1546x423) and mobile preview for each candidate name.

    python make_brand.py out_dir
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FD = "/usr/share/fonts/opentype/inter"


def f(size, w="Bold"):
    return ImageFont.truetype(f"{FD}/Inter-{w}.otf", size)


def vgrad(w, h, top, bottom):
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return img


def glow(size, center, radius, color, blur, strength=1.0):
    """RGBA glow layer."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color + (int(255 * strength),))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def stars(img, n, seed, box, rmax=3, alpha=200):
    import random
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        r = rnd.choice([1, 1, 1, 2, 2, rmax])
        a = rnd.randint(alpha // 3, alpha)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 238, 255, a))


# ----------------------------------------------------------------------------- candidates
CANDIDATES = {
    "driftlight": dict(
        name="Driftlight",
        tagline="Original ambient music for deep sleep",
        sub="New 1–8 hour journeys every few days",
        top=(18, 16, 48), bottom=(58, 36, 92), accent=(255, 204, 150), text=(246, 240, 255),
        muted=(176, 166, 210),
    ),
    "night_hollow": dict(
        name="Night Hollow",
        tagline="Calm nights in the forest. Rain, wind & soft music.",
        sub="Long sleep ambiences · 1–8 hours",
        top=(8, 20, 28), bottom=(14, 52, 58), accent=(214, 236, 220), text=(236, 246, 240),
        muted=(140, 178, 168),
    ),
    "slowmoon": dict(
        name="Slowmoon",
        tagline="Slow music for slow nights",
        sub="Sleep · Study · Unwind",
        top=(10, 12, 30), bottom=(26, 30, 66), accent=(250, 236, 200), text=(248, 244, 232),
        muted=(160, 160, 200),
    ),
}


# ----------------------------------------------------------------------------- marks
def mark_driftlight(size, c):
    """A soft horizon arc with a drifting light above it."""
    s = size
    img = vgrad(s, s, c["top"], c["bottom"]).convert("RGBA")
    stars(img, 90, 3, (0, 0, s, s * 0.6), alpha=150)
    cx, cy = s * 0.5, s * 0.40
    img.alpha_composite(glow((s, s), (cx, cy), s * 0.13, c["accent"], s * 0.09, 0.9))
    img.alpha_composite(glow((s, s), (cx, cy), s * 0.055, (255, 245, 230), s * 0.012))
    d = ImageDraw.Draw(img)
    # horizon: dark hill arc
    d.ellipse([-s * 0.25, s * 0.62, s * 1.25, s * 1.6], fill=(12, 10, 30))
    # thin accent rim on the horizon
    rim = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse([-s * 0.25, s * 0.62, s * 1.25, s * 1.6], outline=c["accent"] + (200,), width=int(s * 0.012))
    img.alpha_composite(rim.filter(ImageFilter.GaussianBlur(s * 0.006)))
    return img.convert("RGB")


def mark_night_hollow(size, c):
    """Moon over a hollow between two pine ridges."""
    s = size
    img = vgrad(s, s, c["top"], c["bottom"]).convert("RGBA")
    stars(img, 70, 5, (0, 0, s, s * 0.55), alpha=140)
    mx, my, mr = s * 0.5, s * 0.36, s * 0.11
    img.alpha_composite(glow((s, s), (mx, my), mr * 1.9, c["accent"], s * 0.07, 0.5))
    d = ImageDraw.Draw(img)
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=c["accent"])
    # ridges (two overlapping dark triangles making a hollow in the middle)
    dark = (6, 14, 18)
    d.polygon([(-s * 0.1, s * 1.1), (-s * 0.1, s * 0.62), (s * 0.18, s * 0.46), (s * 0.42, s * 0.70), (s * 0.5, s * 1.1)], fill=dark)
    d.polygon([(s * 1.1, s * 1.1), (s * 1.1, s * 0.60), (s * 0.84, s * 0.44), (s * 0.58, s * 0.70), (s * 0.5, s * 1.1)], fill=dark)
    # ground closes the hollow
    d.rectangle([0, s * 0.70, s, s], fill=dark)
    # pines standing in the hollow (silhouettes in front of the moon glow)
    for px, py, ph in [(0.36, 0.52, 0.26), (0.44, 0.58, 0.20), (0.56, 0.56, 0.22), (0.64, 0.50, 0.28)]:
        x, y, h = px * s, py * s, ph * s
        d.rectangle([x - h * 0.03, y + h * 0.6, x + h * 0.03, s * 0.72], fill=dark)
        for k in range(4):
            w = h * (0.16 + 0.09 * k)
            yy = y + k * h * 0.17
            d.polygon([(x, yy), (x - w, yy + h * 0.34), (x + w, yy + h * 0.34)], fill=dark)
    return img.convert("RGB")


def mark_slowmoon(size, c):
    """Crescent made from two circles, with slow concentric rings."""
    s = size
    img = vgrad(s, s, c["top"], c["bottom"]).convert("RGBA")
    stars(img, 60, 9, (0, 0, s, s), alpha=120)
    cx, cy, r = s * 0.5, s * 0.5, s * 0.21
    for i, a in enumerate([28, 20, 12]):
        rr = r * (1.55 + i * 0.35)
        ring = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=c["accent"] + (a * 4,), width=int(s * 0.006))
        img.alpha_composite(ring)
    img.alpha_composite(glow((s, s), (cx, cy), r * 1.6, c["accent"], s * 0.06, 0.45))
    # crescent = full disc minus an offset disc, drawn as one mask so the glow shows through
    ox, cut = cx + r * 0.42, r * 0.86
    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    md.ellipse([ox - cut, cy - cut - r * 0.1, ox + cut, cy + cut - r * 0.1], fill=0)
    moon = Image.new("RGBA", (s, s), c["accent"] + (255,))
    img.paste(moon, (0, 0), mask)
    return img.convert("RGB")


MARKS = {"driftlight": mark_driftlight, "night_hollow": mark_night_hollow, "slowmoon": mark_slowmoon}


# ----------------------------------------------------------------------------- outputs
def logo(key, out, size=800):
    c = CANDIDATES[key]
    img = MARKS[key](size * 2, c).resize((size, size), Image.LANCZOS)
    img.save(f"{out}/{key}_logo_800.png")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size, size], fill=255)
    prev = Image.new("RGB", (size, size), (255, 255, 255))
    prev.paste(img, (0, 0), m)
    prev.save(f"{out}/{key}_logo_circle_preview.png")


def banner(key, out):
    c = CANDIDATES[key]
    W, H = 2560, 1440
    img = vgrad(W, H, c["top"], c["bottom"]).convert("RGBA")
    stars(img, 700, 11, (0, 0, W, H * 0.75), alpha=170)
    sx0, sy0 = (W - 1546) // 2, (H - 423) // 2
    # the mark, small, on the left of the safe area
    mk = MARKS[key](800, c).resize((340, 340), Image.LANCZOS)
    mm = Image.new("L", (340, 340), 0)
    ImageDraw.Draw(mm).ellipse([0, 0, 340, 340], fill=255)
    img.paste(mk, (sx0 + 40, sy0 + 42), mm)
    d = ImageDraw.Draw(img)
    tx = sx0 + 440
    d.text((tx, sy0 + 70), c["name"], font=f(130, "Bold"), fill=c["text"])
    d.text((tx + 4, sy0 + 230), c["tagline"], font=f(44, "Medium"), fill=c["muted"])
    d.text((tx + 4, sy0 + 300), c["sub"], font=f(36, "SemiBold"), fill=c["accent"])
    # dark ground band at the bottom (TV only)
    d.rectangle([0, H * 0.86, W, H], fill=(8, 8, 20))
    img = img.convert("RGB")
    img.save(f"{out}/{key}_banner_2560x1440.png")
    img.crop((sx0, sy0, sx0 + 1546, sy0 + 423)).save(f"{out}/{key}_banner_mobile_preview.png")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    for key in CANDIDATES:
        logo(key, out)
        banner(key, out)
    print("ok", list(CANDIDATES))
