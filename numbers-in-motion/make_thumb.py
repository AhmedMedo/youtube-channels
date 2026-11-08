"""Thumbnail: crop of a mid-video frame on the left + big headline panel on the right. 1280x720."""
import sys
from PIL import Image, ImageDraw
sys.argv += [] ; from render_v2 import font
src, out, l1, l2, l3 = sys.argv[1:6]
f = Image.open(src).convert("RGB")
W, H = 1280, 720
crop = f.crop((0, 175, 1300, 1080)).resize((int(1300 * 720 / 905), 720))
img = Image.new("RGB", (W, H), (11, 13, 18)); img.paste(crop, (0, 0))
d = ImageDraw.Draw(img)
d.rectangle([700, 0, W, H], fill=(11, 13, 18)); d.rectangle([700, 0, 708, H], fill=(255, 200, 60))
y = 120
for txt, sz, col in [(l1, 92, (255, 255, 255)), (l2, 92, (255, 200, 60)), (l3, 58, (255, 255, 255))]:
    for line in txt.split("|"):
        d.text((740, y), line, font=font(sz, "Bold"), fill=col); y += int(sz * 1.12)
    y += 20
img.save(out, quality=92); print(out)
