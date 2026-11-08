"""Driftlight — cute / funny logo concepts (flat, thick outlines, sleepy characters).

    python logo_concepts.py out_dir     → 4 concepts, 800x800 + circle previews + contact sheet
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FD = "/usr/share/fonts/opentype/inter"
S = 3200  # draw at 4x then downsample to 800

NAVY = (24, 22, 58)
NAVY2 = (44, 38, 96)
CREAM = (255, 236, 180)
CREAM_D = (236, 196, 120)
INK = (26, 20, 46)
PINK = (255, 150, 150)
WHITE = (250, 248, 255)
SKY_STAR = (255, 226, 150)


def f(size, w="Bold"):
    return ImageFont.truetype(f"{FD}/Inter-{w}.otf", size)


def bg(top=NAVY, bottom=NAVY2):
    img = Image.new("RGB", (S, S), top)
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def sparkle(d, x, y, r, col=SKY_STAR, w=0):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i
        rr = r if i % 2 == 0 else r * 0.38
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def small_stars(d, seed, n=14, box=(0, 0, S, S)):
    import random
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.uniform(box[0], box[2]), rnd.uniform(box[1], box[3])
        if math.hypot(x - S / 2, y - S / 2) < S * 0.33:
            continue
        sparkle(d, x, y, rnd.uniform(22, 60), col=(200, 196, 240))


def closed_eye(d, x, y, w, lw, flip=False):
    """A happy closed eye: a downward arc (sleeping smile shape)."""
    d.arc([x - w, y - w * 0.9, x + w, y + w * 0.9], 200, 340, fill=INK, width=lw)


def blush(d, x, y, r):
    d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=PINK)


def mouth_smile(d, x, y, w, lw):
    d.arc([x - w, y - w, x + w, y + w * 0.6], 20, 160, fill=INK, width=lw)


def zzz(d, x, y, size, col=CREAM):
    for i, s in enumerate((size, size * 0.72, size * 0.5)):
        d.text((x + i * size * 0.95, y - i * size * 0.95), "z", font=f(int(s)), fill=col)


def nightcap(d, cx, cy, r, lw, col=(120, 110, 220), col2=CREAM):
    """Floppy nightcap on the upper-left of a circle (cx, cy, r): band hugging the rim, tip drooping left."""
    def P(a, k):
        return (cx + r * k * math.cos(math.radians(a)), cy + r * k * math.sin(math.radians(a)))
    tip = (cx - r * 1.45, cy - r * 0.95)
    base = [P(a, 1.0) for a in range(196, 262, 6)]
    ctrl = [P(a, 1.55) for a in range(250, 215, -7)]
    poly = base + ctrl + [tip]
    d.polygon(poly, fill=INK)
    shrink = [(x + (cx - x) * 0.0, y) for x, y in poly]
    d.polygon(poly, fill=INK)
    inner = [P(a, 0.98) for a in range(198, 260, 6)] + [P(a, 1.48) for a in range(249, 216, -7)] + [(tip[0] + r * 0.06, tip[1] + r * 0.05)]
    d.polygon(inner, fill=col)
    # band
    d.arc([cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12], 192, 266, fill=INK, width=int(r * 0.26))
    d.arc([cx - r * 1.1, cy - r * 1.1, cx + r * 1.1, cy + r * 1.1], 194, 264, fill=col2, width=int(r * 0.2))
    # pompom
    pr = r * 0.17
    d.ellipse([tip[0] - pr - lw * 0.6, tip[1] - pr - lw * 0.6, tip[0] + pr + lw * 0.6, tip[1] + pr + lw * 0.6], fill=INK)
    d.ellipse([tip[0] - pr, tip[1] - pr, tip[0] + pr, tip[1] + pr], fill=col2)


def outline_circle(d, x, y, r, fill, lw):
    d.ellipse([x - r - lw, y - r - lw, x + r + lw, y + r + lw], fill=INK)
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


# ----------------------------------------------------------------------------- concepts
def c1_sleepy_moon():
    """Crescent moon with a nightcap, eyes shut, blush, little zzz."""
    img = bg()
    d = ImageDraw.Draw(img)
    small_stars(d, 1)
    cx, cy, r = S * 0.47, S * 0.52, S * 0.26
    # glow
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5], fill=CREAM + (70,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), g.filter(ImageFilter.GaussianBlur(S * 0.03))).convert("RGB"))
    d = ImageDraw.Draw(img)
    # crescent (disc minus offset disc) with ink outline
    lw = int(S * 0.016)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    ox, cr = cx + r * 0.62, r * 0.80
    md.ellipse([ox - cr, cy - cr - r * 0.15, ox + cr, cy + cr - r * 0.15], fill=0)
    outline = mask.filter(ImageFilter.MaxFilter(min(lw * 2 + 1, 61)))
    img.paste(Image.new("RGB", (S, S), INK), (0, 0), outline)
    img.paste(Image.new("RGB", (S, S), CREAM), (0, 0), mask)
    # face on the thick left part of the crescent
    fx = cx - r * 0.42
    closed_eye(d, fx - r * 0.02, cy - r * 0.25, r * 0.16, int(S * 0.012))
    closed_eye(d, fx + r * 0.34, cy - r * 0.32, r * 0.13, int(S * 0.012))
    blush(d, fx - r * 0.12, cy + r * 0.02, r * 0.11)
    mouth_smile(d, fx + r * 0.12, cy + r * 0.12, r * 0.09, int(S * 0.010))
    nightcap(d, cx, cy, r, lw)
    # zzz
    zzz(d, cx + r * 0.55, cy - r * 0.35, S * 0.11)
    return img


def c2_cloud_pillow(transparent=False):
    """A puffy cloud asleep, hugging a star like a pillow."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0)) if transparent else bg((30, 34, 78), (60, 50, 110))
    d = ImageDraw.Draw(img)
    if not transparent:
        small_stars(d, 2)
    cx, cy = S * 0.5, S * 0.56
    lw = int(S * 0.016)
    puffs = [(cx - S * 0.19, cy, S * 0.13), (cx - S * 0.07, cy - S * 0.09, S * 0.16), (cx + S * 0.08, cy - S * 0.06, S * 0.15),
             (cx + S * 0.19, cy + S * 0.02, S * 0.12), (cx, cy + S * 0.05, S * 0.15)]
    for x, y, r in puffs:
        d.ellipse([x - r - lw, y - r - lw, x + r + lw, y + r + lw], fill=INK)
    d.rounded_rectangle([cx - S * 0.26 - lw, cy - S * 0.01, cx + S * 0.26 + lw, cy + S * 0.13 + lw], radius=S * 0.05, fill=INK)
    for x, y, r in puffs:
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE)
    d.rounded_rectangle([cx - S * 0.26, cy - S * 0.01, cx + S * 0.26, cy + S * 0.13], radius=S * 0.05, fill=WHITE)
    # star pillow hugged at the right
    sx, sy = cx + S * 0.2, cy - S * 0.13
    pts = []
    for i in range(10):
        a = -math.pi / 2 + math.pi / 5 * i
        rr = S * 0.11 if i % 2 == 0 else S * 0.05
        pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
    d.polygon(pts, fill=INK)
    pts2 = [(sx + (x - sx) * 0.86, sy + (y - sy) * 0.86) for x, y in pts]
    d.polygon(pts2, fill=CREAM)
    # little arm over the star
    d.rounded_rectangle([sx - S * 0.1, sy + S * 0.03, sx + S * 0.03, sy + S * 0.085], radius=S * 0.03, fill=INK)
    d.rounded_rectangle([sx - S * 0.1 + lw * 0.6, sy + S * 0.03 + lw * 0.6, sx + S * 0.03 - lw * 0.6, sy + S * 0.085 - lw * 0.6], radius=S * 0.025, fill=WHITE)
    # face
    closed_eye(d, cx - S * 0.1, cy - S * 0.03, S * 0.04, int(S * 0.012))
    closed_eye(d, cx + S * 0.0, cy - S * 0.03, S * 0.04, int(S * 0.012))
    blush(d, cx - S * 0.16, cy + S * 0.01, S * 0.03)
    blush(d, cx + S * 0.06, cy + S * 0.01, S * 0.03)
    mouth_smile(d, cx - S * 0.05, cy + S * 0.01, S * 0.025, int(S * 0.009))
    zzz(d, cx - S * 0.3, cy - S * 0.25, S * 0.1)
    return img


def c3_lantern_boat():
    """DriftLIGHT literally: a sleepy little lantern drifting in a paper boat on a calm sea."""
    img = bg((16, 20, 52), (28, 40, 96))
    d = ImageDraw.Draw(img)
    small_stars(d, 3, box=(0, 0, S, S * 0.5))
    lw = int(S * 0.016)
    # sea
    d.rectangle([0, S * 0.66, S, S], fill=(34, 60, 120))
    for i in range(3):
        y = S * (0.70 + i * 0.08)
        for x in range(0, S, int(S * 0.12)):
            d.arc([x, y - S * 0.02, x + S * 0.12, y + S * 0.02], 180, 360, fill=(60, 96, 170), width=int(S * 0.008))
    # boat (paper boat silhouette)
    bx, by = S * 0.5, S * 0.66
    hull = [(bx - S * 0.3, by - S * 0.02), (bx + S * 0.3, by - S * 0.02), (bx + S * 0.18, by + S * 0.1), (bx - S * 0.18, by + S * 0.1)]
    d.polygon(hull, fill=INK)
    hull2 = [(bx - S * 0.27, by), (bx + S * 0.27, by), (bx + S * 0.165, by + S * 0.085), (bx - S * 0.165, by + S * 0.085)]
    d.polygon(hull2, fill=WHITE)
    d.polygon([(bx - S * 0.3, by - S * 0.02), (bx - S * 0.02, by - S * 0.02), (bx - S * 0.02, by - S * 0.2)], fill=INK)
    d.polygon([(bx - S * 0.27, by - S * 0.028), (bx - S * 0.03, by - S * 0.028), (bx - S * 0.03, by - S * 0.17)], fill=(226, 224, 240))
    # lantern body (round, glowing) sitting in the boat
    lx, ly, lr = bx + S * 0.08, by - S * 0.17, S * 0.15
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([lx - lr * 2.2, ly - lr * 2.2, lx + lr * 2.2, ly + lr * 2.2], fill=CREAM + (110,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), g.filter(ImageFilter.GaussianBlur(S * 0.04))).convert("RGB"))
    d = ImageDraw.Draw(img)
    # redraw boat bits over the glow
    d.polygon(hull, fill=INK)
    d.polygon(hull2, fill=WHITE)
    d.polygon([(bx - S * 0.3, by - S * 0.02), (bx - S * 0.02, by - S * 0.02), (bx - S * 0.02, by - S * 0.2)], fill=INK)
    d.polygon([(bx - S * 0.27, by - S * 0.028), (bx - S * 0.03, by - S * 0.028), (bx - S * 0.03, by - S * 0.17)], fill=(226, 224, 240))
    outline_circle(d, lx, ly, lr, CREAM, lw)
    # lantern top knob
    d.rounded_rectangle([lx - lr * 0.35, ly - lr * 1.25, lx + lr * 0.35, ly - lr * 0.9], radius=lr * 0.1, fill=INK)
    d.rounded_rectangle([lx - lr * 0.3, ly - lr * 1.2, lx + lr * 0.3, ly - lr * 0.95], radius=lr * 0.08, fill=CREAM_D)
    d.arc([lx - lr * 0.35, ly - lr * 1.75, lx + lr * 0.35, ly - lr * 1.1], 180, 360, fill=INK, width=int(lw * 0.8))
    # face
    closed_eye(d, lx - lr * 0.35, ly - lr * 0.1, lr * 0.22, int(S * 0.012))
    closed_eye(d, lx + lr * 0.35, ly - lr * 0.1, lr * 0.22, int(S * 0.012))
    blush(d, lx - lr * 0.55, ly + lr * 0.2, lr * 0.16)
    blush(d, lx + lr * 0.55, ly + lr * 0.2, lr * 0.16)
    mouth_smile(d, lx, ly + lr * 0.3, lr * 0.14, int(S * 0.009))
    zzz(d, lx + lr * 1.3, ly - lr * 0.9, S * 0.1)
    return img


def c4_sheep_on_moon():
    """A sheep who gave up counting and fell asleep on the crescent."""
    img = bg((28, 20, 60), (70, 40, 100))
    d = ImageDraw.Draw(img)
    small_stars(d, 4)
    lw = int(S * 0.016)
    cx, cy, r = S * 0.5, S * 0.56, S * 0.27
    # crescent lying like a hammock (rotated: opening up)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    md.ellipse([cx - r * 0.82, cy - r * 1.35, cx + r * 0.82, cy + r * 0.3], fill=0)
    outline = mask.filter(ImageFilter.MaxFilter(min(lw * 2 + 1, 61)))
    img.paste(Image.new("RGB", (S, S), INK), (0, 0), outline)
    img.paste(Image.new("RGB", (S, S), CREAM), (0, 0), mask)
    d = ImageDraw.Draw(img)
    # sheep body: fluffy blob
    sx, sy = cx - S * 0.02, cy - S * 0.03
    puffs = [(sx - S * 0.1, sy, S * 0.07), (sx - S * 0.04, sy - S * 0.06, S * 0.075), (sx + S * 0.04, sy - S * 0.055, S * 0.075),
             (sx + S * 0.1, sy, S * 0.07), (sx, sy + S * 0.02, S * 0.085), (sx - S * 0.06, sy + S * 0.04, S * 0.06), (sx + S * 0.06, sy + S * 0.04, S * 0.06)]
    for x, y, rr in puffs:
        d.ellipse([x - rr - lw, y - rr - lw, x + rr + lw, y + rr + lw], fill=INK)
    for x, y, rr in puffs:
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=WHITE)
    # legs dangling over the moon's edge
    for lx_ in (sx - S * 0.05, sx + S * 0.03):
        d.rounded_rectangle([lx_ - S * 0.016, sy + S * 0.06, lx_ + S * 0.016, sy + S * 0.16], radius=S * 0.015, fill=INK)
    # head (dark face, little ears)
    hx, hy, hr = sx + S * 0.15, sy - S * 0.03, S * 0.085
    for ex in (-1, 1):
        d.ellipse([hx + ex * hr * 1.0 - hr * 0.45, hy - hr * 0.2, hx + ex * hr * 1.0 + hr * 0.45, hy + hr * 0.25], fill=INK)
        d.ellipse([hx + ex * hr * 1.0 - hr * 0.3, hy - hr * 0.1, hx + ex * hr * 1.0 + hr * 0.3, hy + hr * 0.15], fill=(150, 130, 170))
    outline_circle(d, hx, hy, hr, (112, 98, 136), lw)
    # wool tuft on head
    d.ellipse([hx - hr * 0.5, hy - hr * 1.1, hx + hr * 0.5, hy - hr * 0.3], fill=INK)
    d.ellipse([hx - hr * 0.42, hy - hr * 1.02, hx + hr * 0.42, hy - hr * 0.38], fill=WHITE)
    # closed eyes (light on dark) + blush
    for ex in (-0.35, 0.35):
        d.arc([hx + ex * hr - hr * 0.22, hy - hr * 0.25, hx + ex * hr + hr * 0.22, hy + hr * 0.15], 200, 340, fill=CREAM, width=int(S * 0.009))
    blush(d, hx - hr * 0.55, hy + hr * 0.3, hr * 0.18)
    blush(d, hx + hr * 0.55, hy + hr * 0.3, hr * 0.18)
    zzz(d, hx + hr * 1.3, hy - hr * 1.6, S * 0.1)
    # tiny "1 2 3 ..." gave-up gag
    d.text((cx - r * 0.95, cy - r * 1.05), "1… 2… 3…", font=f(int(S * 0.055), "SemiBold"), fill=(170, 160, 220))
    return img


CONCEPTS = {"1_sleepy_moon": c1_sleepy_moon, "2_cloud_pillow": c2_cloud_pillow,
            "3_lantern_boat": c3_lantern_boat, "4_sheep_on_moon": c4_sheep_on_moon}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    sheet = Image.new("RGB", (4 * 420 + 20, 440), (255, 255, 255))
    for i, (k, fn) in enumerate(CONCEPTS.items()):
        img = fn().resize((800, 800), Image.LANCZOS)
        img.save(f"{out}/{k}.png")
        m = Image.new("L", (800, 800), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 800, 800], fill=255)
        prev = Image.new("RGB", (800, 800), (255, 255, 255))
        prev.paste(img, (0, 0), m)
        prev.save(f"{out}/{k}_circle.png")
        sheet.paste(prev.resize((400, 400)), (20 + i * 420, 20))
    sheet.save(f"{out}/concepts_sheet.png")
    print("ok")
