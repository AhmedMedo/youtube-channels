#!/usr/bin/env python3
"""Whiteboard-animation demo: a hand draws line art and handwrites text on paper.
Everything is generated here (no stock assets): strokes are polylines with a hand-drawn wobble,
text is revealed column by column, and a drawn hand+pencil follows the pen tip."""
import math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
PAPER, INK, RED, BLUE = (248, 246, 240), (28, 28, 32), (214, 69, 65), (46, 104, 196)
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
sys.path.insert(0, os.path.join(HERE, "..", "shared"))
import audio


def font(size, name="permanent-marker-latin-400-normal"):
    return ImageFont.truetype(os.path.join(FD, name + ".ttf"), size)


# ----------------------------------------------------------------- geometry helpers
def wobble(pts, amp=2.2, freq=0.07, seed=0.0):
    """Nudge a polyline so it reads as hand-drawn rather than CAD."""
    out = []
    for i, (x, y) in enumerate(pts):
        a = math.sin(i * freq * 6.3 + seed) * amp + math.sin(i * freq * 2.1 + seed * 2) * amp * 0.6
        b = math.cos(i * freq * 5.1 + seed * 1.7) * amp
        out.append((x + a, y + b))
    return out


def resample(pts, step=4.0):
    """Even spacing, so the pen moves at a constant speed."""
    out, carry = [pts[0]], 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-6:
            continue
        t = (step - carry) / seg
        while t <= 1.0:
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            t += step / seg
        carry = (carry + seg) % step
    out.append(pts[-1])
    return out


def circle(cx, cy, r, n=72, a0=0.0, a1=2 * math.pi):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def rrect(x0, y0, x1, y1, r=28, n=10):
    p = []
    for (cx, cy, a) in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        p += circle(cx, cy, r, n, a, a + math.pi / 2)
    return p + [p[0]]


def line(x0, y0, x1, y1):
    return [(x0, y0), (x1, y1)]


# ----------------------------------------------------------------- the hand
def make_hand(angle_deg=52):
    """A cartoon fist holding a pencil. Built with the pencil pointing straight up, then rotated
    so the tip is the contact point and the arm trails off the bottom-right."""
    S = 1500
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = S // 2, S // 2                      # pencil tip, canonical
    skin, sleeve, wood = (247, 214, 182), (232, 236, 244), (238, 198, 124)
    # arm first, so the fist overlaps it
    d.rounded_rectangle([cx - 40, cy - 800, cx + 300, cy - 300], radius=80, fill=sleeve, outline=INK, width=7)
    # pencil
    d.polygon([(cx, cy), (cx - 22, cy - 78), (cx + 22, cy - 78)], fill=(248, 230, 196), outline=INK)
    d.polygon([(cx, cy), (cx - 9, cy - 32), (cx + 9, cy - 32)], fill=INK)
    d.rectangle([cx - 22, cy - 452, cx + 22, cy - 76], fill=wood, outline=INK, width=5)
    d.rectangle([cx - 22, cy - 494, cx + 22, cy - 450], fill=(196, 200, 208), outline=INK, width=5)
    d.rounded_rectangle([cx - 22, cy - 530, cx + 22, cy - 488], radius=14, fill=(236, 130, 120), outline=INK, width=5)
    d.line([(cx - 8, cy - 447), (cx - 8, cy - 90)], fill=(208, 168, 96), width=4)
    # fist
    d.rounded_rectangle([cx - 158, cy - 385, cx + 158, cy - 145], radius=74, fill=skin, outline=INK, width=7)
    for i in range(3):
        y = cy - 325 + i * 58
        d.line([(cx - 120, y), (cx + 128, y)], fill=(214, 176, 146), width=5)
    # thumb across the barrel
    d.rounded_rectangle([cx - 196, cy - 316, cx + 36, cy - 232], radius=42, fill=skin, outline=INK, width=7)
    lay = lay.rotate(-(90 + angle_deg), resample=Image.BICUBIC, center=(cx, cy))
    k = 0.8                                      # scale the whole hand down a little
    lay = lay.resize((int(S * k), int(S * k)), Image.LANCZOS)
    return lay, (cx * k, cy * k)


HAND, HAND_TIP = make_hand()


def put_hand(img, at, lift=0.0):
    if lift >= 1:
        return
    x, y = at[0] - HAND_TIP[0], at[1] - HAND_TIP[1]
    lay = HAND
    if lift > 0:                                        # fade out when the pen leaves the paper
        lay = HAND.copy()
        lay.putalpha(HAND.getchannel("A").point(lambda v: int(v * (1 - lift))))
    img.alpha_composite(lay, (int(x), int(y)))


# ----------------------------------------------------------------- items
class Stroke:
    """A polyline drawn progressively."""

    def __init__(self, pts, width=9, color=INK, speed=1.0, wob=2.2, seed=0.0):
        self.pts = resample(wobble(pts, wob, seed=seed), 4.0)
        self.w, self.c, self.speed = width, color, speed
        self.dur = max(0.18, len(self.pts) * 0.0042 / speed)

    def draw(self, d, frac):
        n = max(2, int(len(self.pts) * frac))
        d.line(self.pts[:n], fill=self.c, width=self.w, joint="curve")
        return self.pts[n - 1]


class Text:
    """Handwriting: the glyphs are revealed left to right."""

    def __init__(self, txt, xy, size, fname="permanent-marker-latin-400-normal", color=INK, anchor="mm", speed=1.0):
        self.img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(self.img)
        dd.text(xy, txt, font=font(size, fname), fill=color, anchor=anchor)
        self.box = self.img.getbbox()
        self.dur = max(0.4, (self.box[2] - self.box[0]) * 0.0024 / speed)

    def draw_into(self, canvas, frac):
        x0, y0, x1, y1 = self.box
        cut = int(x0 + (x1 - x0) * min(1.0, frac))
        canvas.alpha_composite(self.img.crop((x0, y0, cut + 1, y1)), (x0, y0))
        return (cut, y0 + (y1 - y0) * 0.72)


class Pop:
    """Something that simply appears (a stamp), no pen."""

    def __init__(self, img, at, dur=0.45):
        self.img, self.at, self.dur = img, at, dur

    def draw_into(self, canvas, frac):
        k = 1 - (1 - min(1.0, frac)) ** 3
        s = max(1, int(self.img.width * (0.6 + 0.4 * k)))
        im = self.img.resize((s, int(self.img.height * s / self.img.width)))
        if frac < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
        canvas.alpha_composite(im, (int(self.at[0] - im.width / 2), int(self.at[1] - im.height / 2)))
        return None


def paper():
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    d = ImageDraw.Draw(img)
    for i in range(0, W, 7):                      # faint fibre texture
        d.line([(i, 0), (i, H)], fill=(243, 241, 235, 255), width=1)
    return img


# ----------------------------------------------------------------- the demo script
def build():
    items = []                                     # (item, start, gap_after)
    t = 0.3

    def add(it, gap=0.18):
        nonlocal t
        items.append((it, t))
        t += it.dur + gap
        return it

    add(Text("FACELESS", (W / 2, 300), 170, "permanent-marker-latin-400-normal"), 0.05)
    add(Text("YOUTUBE", (W / 2, 450), 170, "permanent-marker-latin-400-normal"), 0.1)
    add(Stroke(line(250, 540, 830, 548), 12, RED, speed=2.2, wob=4), 0.35)
    add(Text("no camera.  no face.", (W / 2, 640), 76, "caveat-latin-700-normal", (90, 92, 104)), 0.5)

    cx, cy = W / 2, 980                           # camera drawing
    add(Stroke(rrect(cx - 300, cy - 180, cx + 300, cy + 180, 40), 10, speed=1.5, seed=1), 0.06)
    add(Stroke(rrect(cx - 120, cy - 250, cx + 40, cy - 170, 20), 10, speed=1.6, seed=2), 0.06)
    add(Stroke(circle(cx, cy, 128), 10, speed=1.6, seed=3), 0.06)
    add(Stroke(circle(cx, cy, 74), 9, speed=1.7, seed=4), 0.06)
    add(Stroke(circle(cx + 198, cy - 96, 26), 8, speed=1.8, seed=5), 0.3)
    add(Stroke(line(cx - 330, cy - 210, cx + 330, cy + 210), 26, RED, speed=2.6, wob=5, seed=6), 0.05)
    add(Stroke(line(cx + 330, cy - 210, cx - 330, cy + 210), 26, RED, speed=2.6, wob=5, seed=7), 0.45)

    add(Text("JUST  DATA.", (W / 2, 1545), 132, "permanent-marker-latin-400-normal", BLUE), 0.15)
    add(Stroke(circle(W / 2, 1545, 258, a0=-0.35, a1=2 * math.pi - 0.2) + [(W / 2 + 278, 1492)], 11, BLUE, speed=2.4, wob=6, seed=8), 0.3)
    add(Text("Numbers in Motion", (W / 2, 1866), 74, "caveat-latin-700-normal", (90, 92, 104)), 0.2)
    return items, t + 1.4


def render(out):
    items, total = build()
    canvas = paper()
    ev = []
    for it, s in items:
        ev.append((int(s * FPS), "pop", 0.22 if isinstance(it, Text) else 0.3))
    frames = int(total * FPS)
    tmp = tempfile.mkdtemp()
    silent, wav = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    done = 0
    for fi in range(frames):
        t = fi / FPS
        while done < len(items) and t >= items[done][1] + items[done][0].dur:
            it = items[done][0]                    # bake the finished item into the canvas
            if isinstance(it, Stroke):
                ImageDraw.Draw(canvas).line(it.pts, fill=it.c, width=it.w, joint="curve")
            else:
                it.draw_into(canvas, 1.0)
            done += 1
        img = canvas.copy()
        tip = None
        for it, s in items[done:]:
            if t < s:
                break
            frac = (t - s) / it.dur
            if isinstance(it, Stroke):
                tip = it.draw(ImageDraw.Draw(img), frac)
            else:
                tip = it.draw_into(img, frac)
        if tip:
            put_hand(img, tip)
        elif done < len(items):                    # pen hovers to the next start
            nxt = items[done]
            lift = max(0.0, min(1.0, (nxt[1] - t) / 0.3))
            start = nxt[0].pts[0] if isinstance(nxt[0], Stroke) else (nxt[0].box[0], nxt[0].box[3])
            put_hand(img, start, lift)
        ff.stdin.write(img.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    audio.write_wav(wav, audio.mix(total, ev))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "128k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("->", out, round(total, 1), "s")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/wb/demo.mp4")
