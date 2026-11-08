# ytpipe — faceless data-viz video pipeline

Turns any tidy CSV (`entity, group, year, value`) into a 1080p racing-bar-chart video,
a thumbnail, and ready-to-paste YouTube metadata. No voice, no face, fully reproducible.

## Install
```bash
pip install pandas numpy pillow gapminder   # gapminder = sample real-world data
# ffmpeg must be on PATH
```

## One video, end to end
```bash
python export_gapminder.py pop data/population.csv

python render.py --csv data/population.csv \
  --title "Most Populous Countries in the World" --subtitle "1952 – 2007 · Top 10" \
  --source "Gapminder" --channel "YOUR CHANNEL" \
  --out out/population.mp4 --top 10 --seconds-per-step 2 --fps 30 \
  --music assets/track.mp3 \
  --thumb-text "BIGGEST
COUNTRIES
1952→2007"

python metadata.py --csv data/population.csv --topic "Most Populous Countries" \
  --unit people --source "Gapminder (gapminder.org)" --out out/population_meta.txt
```

## Bring your own data
Any CSV with these columns works:

| entity | group (optional, drives colors) | year | value |
|---|---|---|---|
| China | Asia | 1952 | 556263527 |

Good public sources (download the CSV manually and drop it in `data/`):
Our World in Data, World Bank, UN Data, IMF WEO, Statista (free tier), Wikipedia tables.
Yearly data gives smoother videos than 5-yearly; `--seconds-per-step` controls pace
(1.0–1.5 s per year is typical for a 60–90 s video over 60 years).

## Knobs worth knowing
- `--top` 10 for 16:9; 8 looks better if names are long.
- `--seconds-per-step` controls total length: steps × seconds + intro + outro.
- `--music` loops/trims any audio file (use royalty-free or your own Suno track with a commercial plan).
- Colors per group live in `GROUP_COLORS` in `render.py`; theme in the constants at the top.

## Originality checklist (YouTube "inauthentic content" policy)
- Real dataset, cited on screen (`--source`) and in the description.
- Vary the visual: top-N, theme, chart type, pace, music — never the same template 50 times.
- Add one line of real insight in the description (metadata.py drafts it; edit it).
- Disclose AI-generated audio in the upload form if the music is AI-made.
