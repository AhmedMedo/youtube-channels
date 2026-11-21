"""Numbers in Motion — channel logo (800x800) and banner (2560x1440, safe area 1546x423)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BG = (14, 16, 22)
FG = (240, 240, 245)
MUTED = (140, 145, 160)
BARS = [(255, 111, 97), (91, 155, 255), (255, 196, 61), (87, 212, 148)]
FD = "/usr/share/fonts/opentype/inter"


def f(size, w="Bold"):
    return ImageFont.truetype(f"{FD}/Inter-{w}.otf", size)


def logo(path, size=800):
    s = size * 4
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)
    # everything fits inside the circle YouTube crops to (radius 0.5s, keep within ~0.36s)
    bar_h = int(s * 0.105)
    gap = int(s * 0.045)
    lengths = [0.56, 0.44, 0.33, 0.23]
    total_h = 4 * bar_h + 3 * gap
    top = (s - total_h) // 2
    left = int(s * 0.22)
    for i, (L, c) in enumerate(zip(lengths, BARS)):
        y = top + i * (bar_h + gap)
        d.rounded_rectangle([left, y, left + int(s * L), y + bar_h], radius=bar_h // 2, fill=c)
    # small motion tick ahead of the leader
    x1 = left + int(s * lengths[0])
    tri = [(x1 + int(s * 0.025), top + bar_h * 0.15), (x1 + int(s * 0.075), top + bar_h / 2),
           (x1 + int(s * 0.025), top + bar_h * 0.85)]
    d.polygon(tri, fill=BARS[0])
    img = img.resize((size, size), Image.LANCZOS)
    img.save(path)
    # circle preview
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size, size], fill=255)
    prev = Image.new("RGB", (size, size), (255, 255, 255)); prev.paste(img, (0, 0), m)
    prev.save(path.replace(".png", "_circle_preview.png"))


def banner(path):
    W, H = 2560, 1440
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # faint background racing bars across the whole width (visible on TV only)
    import random
    random.seed(7)
    sy0_ = (H - 423) // 2
    for i in range(14):
        y = 120 + i * 92
        if sy0_ - 70 < y < sy0_ + 423 + 10:
            continue
        L = random.randint(500, 2300)
        c = BARS[i % 4]
        faint = tuple(int(BG[j] + (c[j] - BG[j]) * 0.10) for j in range(3))
        d.rounded_rectangle([0, y, L, y + 56], radius=28, fill=faint)
    # safe area 1546x423 centered
    sx0, sy0 = (W - 1546) // 2, (H - 423) // 2
    # mini bars icon on the left of safe area
    bx = sx0 + 40
    by = sy0 + 105
    for i, (L, c) in enumerate(zip([250, 195, 150, 105], BARS)):
        y = by + i * 56
        d.rounded_rectangle([bx, y, bx + L, y + 40], radius=20, fill=c)
    tx = bx + 320
    d.text((tx, sy0 + 85), "Numbers in Motion", font=f(118, "Bold"), fill=FG)
    d.text((tx + 4, sy0 + 235), "Real data. 10 rounds. Only one survives.",
           font=f(46, "Medium"), fill=MUTED)
    d.text((tx + 4, sy0 + 305), "New episode every Tuesday, Thursday & Saturday",
           font=f(36, "SemiBold"), fill=BARS[2])
    img.save(path)


if __name__ == "__main__":
    import os
    os.makedirs("/home/claude/brand/out", exist_ok=True)  # banner text updated 21 Nov 2026: Last Country Standing, 3 episodes a week
    logo("/home/claude/brand/out/logo_800.png")
    banner("/home/claude/brand/out/banner_2560x1440.png")
    # safe-area preview to check what phones see
    b = Image.open("/home/claude/brand/out/banner_2560x1440.png")
    b.crop(((2560 - 1546) // 2, (1440 - 423) // 2, (2560 + 1546) // 2, (1440 + 423) // 2)).save(
        "/home/claude/brand/out/banner_mobile_preview.png")
    print("ok")
