"""Promo extras for one episode: vertical Short, black-screen version, Pinterest pin.

    python make_extras.py --episode-dir out/ep001 --base starlight_drift_1h --title "Starlight Drift" \
        --hours 1 --short-start 1230

Inputs expected in --episode-dir (as render_scene.py writes them):
    <base>_loop.mp4   seamless scene loop (video only)
    <base>.wav        full-length music
    <base>_thumb.jpg  thumbnail
Outputs:
    <base>_short.mp4          1080x1920, 45 s, scene strip + big mascot + title, audio from --short-start
    <base>_blackscreen.mp4    full length, black video (tiny file), same music
    <base>_blackscreen_thumb.jpg  thumbnail for the black-screen upload
    <base>_pin.jpg            1000x1500 Pinterest image
"""
import argparse
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
MASCOT = os.path.join(HERE, "brand", "out", "driftlight_character_rgba.png")


def font(size, w="Bold"):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Inter-{w}.otf"), size)


def run(cmd):
    subprocess.run(cmd, check=True)


def overlay_png(path, title, sub):
    """Transparent 1080x1920 overlay: mascot on top, title under the video strip."""
    ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    m = Image.open(MASCOT).convert("RGBA").resize((520, 520), Image.LANCZOS)
    ov.alpha_composite(m, (280, 150))
    d = ImageDraw.Draw(ov)
    f1, f2 = font(78), font(40, "Medium")
    w = d.textlength(title, font=f1)
    for dx, dy in ((3, 3), (-2, 2), (2, -2), (-2, -2)):
        d.text(((1080 - w) / 2 + dx, 1330 + dy), title, font=f1, fill=(0, 0, 0, 170))
    d.text(((1080 - w) / 2, 1330), title, font=f1, fill=(255, 240, 215, 255))
    w2 = d.textlength(sub, font=f2)
    d.text(((1080 - w2) / 2, 1430), sub, font=f2, fill=(200, 200, 235, 255))
    cta = "full version on the channel  →"
    w3 = d.textlength(cta, font=f2)
    d.text(((1080 - w3) / 2, 1700), cta, font=f2, fill=(255, 236, 180, 255))
    ov.save(path)


def make_short(ep, base, title, hours, start, length=45):
    loop = os.path.join(ep, f"{base}_loop.mp4")
    wav = os.path.join(ep, f"{base}.wav")
    ov = os.path.join(ep, f"{base}_short_overlay.png")
    overlay_png(ov, title, f"{hours} hour{'s' if hours > 1 else ''} of original sleep music")
    out = os.path.join(ep, f"{base}_short.mp4")
    # background: the loop scaled to fill 1080x1920 and blurred; middle: sharp 16:9 strip; overlay on top
    fc = ("[0:v]scale=3414:1920,crop=1080:1920,boxblur=20:3,eq=brightness=-0.15[bg];"
          "[0:v]scale=1080:608[strip];[bg][strip]overlay=0:700[v1];[v1][1:v]overlay=0:0,format=yuv420p[v]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", loop, "-i", ov,
         "-ss", str(start), "-i", wav, "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
         "-t", str(length), "-af", f"afade=t=in:d=1,afade=t=out:st={length - 3}:d=3",
         "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-r", "24", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", out])
    return out


def make_blackscreen(ep, base, duration):
    wav = os.path.join(ep, f"{base}.wav")
    out = os.path.join(ep, f"{base}_blackscreen.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=1", "-i", wav,
         "-t", str(duration), "-c:v", "libx264", "-tune", "stillimage", "-crf", "30", "-g", "300", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out])
    return out


def make_blackscreen_thumb(ep, base, title, hours):
    """Dark variant of the episode thumbnail with a BLACK SCREEN badge."""
    from PIL import ImageEnhance
    # the episode thumbnail is already rendered without the small mascot; erase its title, then darken
    im = Image.open(os.path.join(ep, f"{base}_thumb.jpg")).convert("RGB").resize((1280, 720), Image.LANCZOS)
    ImageDraw.Draw(im).rectangle([60, 460, 800, 650], fill=(8, 8, 16))
    im = ImageEnhance.Brightness(im).enhance(0.35)
    m = Image.open(MASCOT).convert("RGBA").resize((460, 460), Image.LANCZOS)
    im.paste(m, (1280 - 470, 30), m)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([66, 370, 470, 440], radius=14, fill=(0, 0, 0, 230), outline=(255, 236, 180, 255), width=3)
    d.text((88, 380), "BLACK SCREEN", font=font(44), fill=(255, 236, 180))
    d.text((70, 470), title, font=font(92), fill=(255, 240, 215))
    d.text((74, 585), f"{hours} Hour{'s' if hours > 1 else ''} · Sleep Music · Screen Off", font=font(40, "Medium"), fill=(200, 200, 230))
    out = os.path.join(ep, f"{base}_blackscreen_thumb.jpg")
    im.save(out, quality=92)
    return out


def make_pin(ep, base, title, hours):
    still = Image.open(os.path.join(ep, f"{base}_still.png")).convert("RGB")
    # 1000x1500: scene crop (top), dark panel with mascot + title (bottom)
    pin = Image.new("RGB", (1000, 1500), (24, 22, 58))
    sc = still.resize((1778, 1000), Image.LANCZOS).crop((389, 0, 1389, 1000))
    pin.paste(sc, (0, 0))
    grad = Image.new("L", (1000, 300), 0)
    gd = ImageDraw.Draw(grad)
    for y in range(300):
        gd.line([(0, y), (1000, y)], fill=int(255 * y / 300))
    pin.paste(Image.new("RGB", (1000, 300), (24, 22, 58)), (0, 700), grad)
    m = Image.open(MASCOT).convert("RGBA").resize((420, 420), Image.LANCZOS)
    pin.paste(m, (290, 820), m)
    d = ImageDraw.Draw(pin)
    f1, f2, f3 = font(72), font(36, "Medium"), font(30, "SemiBold")
    w = d.textlength(title, font=f1)
    d.text(((1000 - w) / 2, 1240), title, font=f1, fill=(255, 240, 215))
    s = f"{hours} hour{'s' if hours > 1 else ''} · original ambient sleep music"
    w2 = d.textlength(s, font=f2)
    d.text(((1000 - w2) / 2, 1330), s, font=f2, fill=(200, 200, 235))
    w3 = d.textlength("Driftlight on YouTube", font=f3)
    d.text(((1000 - w3) / 2, 1410), "Driftlight on YouTube", font=f3, fill=(255, 236, 180))
    out = os.path.join(ep, f"{base}_pin.jpg")
    pin.save(out, quality=90)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--hours", type=int, default=1)
    ap.add_argument("--short-start", type=float, default=1200, help="seconds into the music for the Short")
    a = ap.parse_args()
    print(make_short(a.episode_dir, a.base, a.title, a.hours, a.short_start))
    print(make_blackscreen(a.episode_dir, a.base, a.hours * 3600))
    print(make_blackscreen_thumb(a.episode_dir, a.base, a.title, a.hours))
    print(make_pin(a.episode_dir, a.base, a.title, a.hours))
