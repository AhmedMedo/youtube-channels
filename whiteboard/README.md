# Whiteboard animation (parked idea — 11 Nov 2026)

A hand draws line art and handwrites text on paper, the style used by a lot of Arabic and English
course ads. Built here from scratch with PIL + ffmpeg: no VideoScribe, no Doodly, no stock assets.

`python3 whiteboard.py out.mp4` renders the demo (1080x1920, ~17 s).

## What's in the renderer
- `Stroke` — a polyline drawn progressively; `wobble()` adds a hand-drawn waver so it doesn't look like CAD.
- `Text` — handwriting, revealed left to right out of a rendered glyph mask.
- `make_hand()` — a cartoon fist + pencil, drawn with the pencil pointing up and then rotated so the
  tip is the contact point and the forearm trails off the bottom-right. The tip tracks the pen exactly.
- Finished items are baked into a persistent canvas, so only the item in progress is redrawn per frame.
- Sound comes from `shared/audio.py` (music bed + a soft tick as each item starts).

## Fonts (not committed — fetch them)
```
npm install @fontsource/caveat @fontsource/permanent-marker @fontsource/patrick-hand
npm install @fontsource/cairo @fontsource/tajawal        # Arabic
```
Then convert the woff2 files to ttf with fontTools (`f = TTFont(p); f.flavor = None; f.save(out)`)
into `whiteboard/fonts/`. For Arabic also `pip install arabic_reshaper python-bidi` and pass text
through `get_display(arabic_reshaper.reshape(txt))` — tested and working.

## What is missing
- **Voiceover.** ElevenLabs, OpenAI and Google TTS are all blocked from this workspace
  (connection refused / 403). Ahmed has to generate the audio himself and hand over the mp3;
  the renderer then gets timed to it.
- **Illustrations.** The code draws clean geometric line art. The hand-drawn character work in the
  ads it imitates would have to come in as transparent PNGs and be animated as reveals.

## The alternative, if we ever buy instead of build
Classic scene-by-scene editors: VideoScribe, Doodly, Powtoon, Animaker, Renderforest — they ship
libraries of hand-drawn assets, which is where their look comes from. Newer AI whiteboard generators
take a script or document and return a finished narrated video, voice included. Faster, costs per
video, and the result looks like everyone else's.

## Status
Parked. Ahmed saw the demo on 11 Nov 2026 and wants it kept in the plans, not started yet.
If it goes ahead: English, not Arabic — his target audience is global and Arabic ad rates are lower.
