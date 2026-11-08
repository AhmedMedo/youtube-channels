"""Driftlight — final brand: cloud-and-pillow character. Logo 800x800, banner 2560x1440 (+ previews).

    python final_brand.py out_dir
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

import logo_concepts as lc

FD = "/usr/share/fonts/opentype/inter"


def f(size, w="Bold"):
    return ImageFont.truetype(f"{FD}/Inter-{w}.otf", size)


def logo(out):
    img = lc.c2_cloud_pillow().resize((800, 800), Image.LANCZOS)
    img.save(f"{out}/driftlight_logo_800.png")
    m = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 800, 800], fill=255)
    prev = Image.new("RGB", (800, 800), (255, 255, 255))
    prev.paste(img, (0, 0), m)
    prev.save(f"{out}/driftlight_logo_circle_preview.png")
    # transparent character only (for thumbnails / video watermark)
    lc.c2_cloud_pillow(transparent=True).resize((800, 800), Image.LANCZOS).save(f"{out}/driftlight_character_rgba.png")
    return img


def banner(out):
    W, H = 2560, 1440
    top, bottom = (30, 34, 78), (60, 50, 110)
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    # scattered sparkles (TV area)
    import random
    rnd = random.Random(21)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        if (W - 1546) // 2 - 60 < x < (W + 1546) // 2 + 60 and (H - 423) // 2 - 60 < y < (H + 423) // 2 + 60:
            continue
        lc.sparkle(d, x, y, rnd.uniform(8, 26), col=(150, 146, 210))
    sx0, sy0 = (W - 1546) // 2, (H - 423) // 2
    # character (crop the cloud out of the square concept, keep it large)
    ch = lc.c2_cloud_pillow(transparent=True).crop((int(lc.S * 0.10), int(lc.S * 0.16), int(lc.S * 0.90), int(lc.S * 0.86)))
    ch = ch.resize((int(ch.width * 400 / ch.height), 400), Image.LANCZOS)
    img.paste(ch, (sx0 - 10, sy0 + 8), ch)
    d = ImageDraw.Draw(img)
    tx = sx0 + ch.width - 20
    d.text((tx, sy0 + 78), "Driftlight", font=f(136, "Bold"), fill=(250, 248, 255))
    d.text((tx + 4, sy0 + 240), "Original ambient music for deep sleep", font=f(44, "Medium"), fill=(190, 184, 230))
    d.text((tx + 4, sy0 + 310), "New 1–8 hour journeys every few days  ·  zzz", font=f(36, "SemiBold"), fill=(255, 236, 180))
    img.save(f"{out}/driftlight_banner_2560x1440.png")
    img.crop((sx0, sy0, sx0 + 1546, sy0 + 423)).save(f"{out}/driftlight_banner_mobile_preview.png")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    logo(out)
    banner(out)
    print("ok")
