"""Pre-render square sticker crops of the 50 state flags (Wikimedia Commons files, public domain)."""
import sys, io, os
import cairosvg
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
NAMES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado_designed_by_Andrew_Carlisle_Carson','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia_(U.S._state)','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New_Hampshire','NJ':'New_Jersey','NM':'New_Mexico','NY':'New_York','NC':'North_Carolina','ND':'North_Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode_Island','SC':'South_Carolina','SD':'South_Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West_Virginia','WI':'Wisconsin','WY':'Wyoming'}
# (centre x, centre y, zoom): which square of the flag the round sticker shows
CROP = {'TX': (.33, .5, 1), 'NC': (.33, .5, 1), 'GA': (.33, .5, 1), 'HI': (.33, .5, 1), 'OH': (.3, .5, 1), 'MN': (.3, .5, 1),
        'CO': (.42, .5, 1), 'NV': (.2, .3, 1.6), 'SC': (.42, .5, 1), 'MA': (.5, .5, 1.5), 'IL': (.5, .5, 1.1), 'AK': (.42, .5, 1)}
SEAL = "CT ME MI NY ND PA VT LA DE NJ".split()
for c in SEAL:
    CROP.setdefault(c, (.5, .5, 1.12))
S = 520
for code, nm in NAMES.items():
    png = cairosvg.svg2png(url=os.path.join(src, f"Flag_of_{nm}.svg"), output_height=900, unsafe=False)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    W, H = bg.size
    ax, ay, z = CROP.get(code, (.5, .5, 1))
    side = min(W, H) / z
    x0 = min(max(ax * W - side / 2, 0), W - side)
    y0 = min(max(ay * H - side / 2, 0), H - side)
    bg.crop((int(x0), int(y0), int(x0 + side), int(y0 + side))).resize((S, S), Image.LANCZOS).convert("RGB").save(os.path.join(out, f"{code}.jpg"), quality=90)
print("ok", len(NAMES))
