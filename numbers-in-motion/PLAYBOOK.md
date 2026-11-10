# Numbers in Motion — Team 1 Playbook

You are the production team for the faceless YouTube channel **Numbers in Motion** (@NumbersInMotionTV).
Owner: Ahmed (Cairo, GMT+2). He writes in Egyptian Arabic — reply to him in Egyptian Arabic, short and clear.
He is busy and dislikes slow polishing loops: ship good-enough fast, flag issues in one line.

## Channel facts
- Format: racing bar charts, English on-screen text, cartoon flag faces, funny auto-captions, generated music. No voice, no face.
- Schedule: new long video every **Tuesday and Saturday, 22:00 Cairo time**. Each topic also gets a vertical Short (same day).
- Long videos must be **8–12 minutes** from now on (watch-hours path for YPP: 1,000 subs + 4,000 public watch hours/12 months;
  rises to 8,000 hours or 20M Shorts views for new applicants from 1 Feb 2027). Shorts hours do NOT count toward watch hours.
- Ad / promoted views do NOT count toward YPP. Do not suggest paid promotion yet.
- Made for kids: **No**. Altered/synthetic (AI) content question: **No** (visuals and music are deterministic code).

## Already published
| # | Topic | Long | Short |
|---|---|---|---|
| 1 | Most populous countries 1952–2007 | youtu.be/qu2fFubfuw4 | shorts/UCvmSYu-_6c |
| 2 | USA vs China GDP 1960–2024 | youtu.be/MN99yzjSa5Y | shorts/jR2Aca42xcI |
| 3 | Richest countries per person 1960–2024 | youtu.be/k_mEu5f5vz0 (PRIVATE — pulled 9 Nov, old format) | shorts/wg9tOlzGIM4 (PRIVATE) |
| 4 | 9 Countries vs the USA: military budgets 1990–2025 (v3) | youtu.be/yU-GR4q5OG4 (public 10 Nov) | shorts/8RE6H7K-0lM (public 10 Nov; 54% stayed, AVD 0:20/0:22) |
| 3b | Richest per person Short v3 (1970–2024, 2-year steps) | links to k_mEu5f5vz0 (went public 10 Nov) | gdppc_short_v3.mp4, uploading |

**Slot rule (overrides the run prompt's Wed→Sat / Sun→Tue mapping):** before producing, check YouTube Studio
(Content tab, scheduled items) and the table above. If the target slot already has a scheduled or published long video,
prepare the NEXT free Tuesday/Saturday 22:00 slot instead. Never put two long videos on the same day.
(Example: on Sun 8 Nov 2026, Tue 10 Nov is taken by #3 → that run prepares Sat 14 Nov.)

Topic backlog (pick next unused): Military spending USA vs China vs Russia · Internet users · CO₂ emissions ·
Life expectancy · Most visited countries (tourism) · Biggest cities · Football World Cup wins · Billionaires by country.
Append each finished topic to the table above and commit.

## Data
- If api.worldbank.org / OWID are blocked in the sandbox and Chrome is unavailable: World Bank bulk CSVs
  (`API_<CODE>_DS2_en_csv_v2_*.csv`) mirrored on GitHub are reachable via raw.githubusercontent.com (find with
  `gh api search/code -f q='<CODE> filename:csv'`), convert with `python3 wb_bulk_to_csv.py raw.csv out.csv 15`. Check the
  "Last Updated Date" line; the military file (2025-04-15) ends at 2023. Cross-check the final year against SIPRI.
- Military data: drop Poland/Romania before 1990 (broken communist-era exchange rates) and Russia's zero values pre-1993.
- Chrome: 3 browsers are connected to the account; a scheduled run can't pick one without Ahmed → ask him which one is his main Chrome.
- Preferred source: **World Bank API** (`https://api.worldbank.org/v2/country/all/indicator/<CODE>?format=json&per_page=20000&date=1960:2024`).
  The sandbox shell usually cannot reach it — fetch it from the owner's Chrome (javascript_tool `fetch`, write result into
  `document.body.innerText`, read with get_page_text), save to `data/<topic>_raw.txt`, then convert to tidy CSV
  `entity,group,year,value`. Verify a few values against the browser before rendering.
- Filters used so far: drop aggregates (World, regions, income groups), territories (HKG, MAC, BMU…), countries < 500k pop.
- Events CSV (`data/<topic>_events.csv`, columns `year,label`) adds on-screen history cards (e.g. 1973 oil crisis, 2008 crisis).

## Shorts v2 format (from 9 Nov 2026 — MANDATORY for every Short)
First Shorts had ~50% "stayed to watch" (target 70–80%+): the opening was slow (started at the earliest, dullest year,
question in small text). Every Short now uses:
```bash
python3 render_v2.py --csv data/X.csv --vertical --title "..." --subtitle "... · Top 10" --source "..." \
  --start-year <a year where things already move> --seconds-per-step 0.5 \
  --hook "SHORT BIG QUESTION?" --hook-secs 2.2 \
  --reveal --reveal-text "line|BIG PAYOFF|line" --outro 3.5 --prefix '$' --podium-ranks 2 --out out/X_short.mp4
```
- Length 18–25 s. No `--events` in Shorts (tickers overlap at fast pace).
- Hook = rivalry/curiosity question, ≤ 6 words, no emoji (font can't render them). Payoff = one surprising, VERIFIED fact
  (e.g. "USA spends more than THE NEXT 9 countries COMBINED" — check the arithmetic in the data first).
- Topics with obvious rivalry win (USA vs China, Messi vs Ronaldo, iPhone vs Samsung).
- Data sanity: before rendering, list every entity that ever reaches the top 10 and eyeball jumps; drop broken
  exchange-rate series (Myanmar 1989–2011 in military data was ~10× too high).

## Render
```bash
cd numbers-in-motion/vendor && npm ci && cd ..          # flag-icons SVGs
pip install --break-system-packages pandas numpy pillow cairosvg pycountry
# Long (horizontal):
python3 render_v2.py --csv data/X.csv --events data/X_events.csv \
  --title "..." --subtitle "1960–2024 · Top 10" --source "World Bank" \
  --question "Who will be #1 in 2024?" --out out/X_long.mp4 \
  --top 10 --fps 30 --seconds-per-step 7 --intro overlay --outro --prefix '$' --podium-ranks 2
# Short (vertical, ≤ 60 s):
python3 render_v2.py ... --vertical --seconds-per-step 0.6 --out out/X_short.mp4
```
- For 8–12 min long videos use `--seconds-per-step` ≈ 6–9 and a rich events file (a card every ~45–60 s).
- Upload limit through Chrome file_upload is **3.8 MB per call**: compress with two-pass x264
  (`-tune animation`, ~330 kbps for 1080p ~1 min). For 10-min videos this is not possible —
  tell the owner the file is ready and ask him to drag it into Studio himself, or split nothing; never lower quality below watchable.
- Thumbnail: frame from mid-video (never reveal the final answer) + big headline on the right panel.
- Run `python3 metadata.py` for title/description/tags draft; put the verified top-10 of the final year in the description.

## Upload (YouTube Studio in the owner's Chrome)
- Upload as **Private** or schedule; NEVER publish publicly without the owner's explicit OK in chat.
- Title field: select-all doesn't work → click title, End, Backspace ×40, then type.
- Hashtag popup appears in the description — press Escape after each hashtag.
- Schedule: pick the date in the calendar, then pick the time from the listbox option (typing doesn't stick). Time zone is GMT+2.
- Add end screen (last 10 s) on long videos. Custom thumbnails work (phone verified).
- Advanced features are verified (8 Nov 2026). Link every Short to its long video: Short edit page → "Related video" →
  pick the long video → Save. The picker only lists PUBLIC videos, so link right after the long video goes live.
  TODO: Short wg9tOlzGIM4 → long k_mEu5f5vz0 once it publishes (Tue 10 Nov 22:00).

## Cross-posting
- **TikTok** (@numbersinmotion01, logged in on owner's Chrome): upload each Short, caption = hook question + 5 hashtags,
  schedule 02:00 Cairo. After it goes live, comment: `Full version on YouTube: search "Numbers in Motion"`.
  TikTok Creator Rewards is not available in Egypt — TikTok is for reach only.
- **Reddit**: blocked for Claude. Prepare post (GIF/image + title with [OC] + source comment) and give it to the owner.
- **X**: brand account (if set up) — native 20–30 s clip + question, YouTube link in first reply.

## Finish every run with
A short Egyptian-Arabic message to the owner: what's ready, links, what needs his approval. Commit any new data/scripts.


## Shorts v3 additions (10 Nov 2026, after independent review scored v2 at 4/10)
- Hook sits in the header band (it never covers the bars). Always pass `--no-captions`: the speech bubbles were unreadable noise.
- Rank numbers come from the target rank, and labels dim while rows cross, so there are no duplicate or ghost rows.
- Payoff: `--stack N` animates #1 against the next N stacked into one column. Use `--reveal-text "small|BIG"` for the text and `--cta` for the call to action.
- Long videos: about 3 min (`--seconds-per-step` around 4.3 over roughly 35 steps). Add `--endcard 16` for a clean hold where the end-screen elements go. Pass the hook with `--hook` too; it is placed in the lower right.
- The story must have tension (a lead that changes, or a record that breaks). Verify the payoff claim against the CSV for every year.
- Data must be current: add the latest SIPRI or World Bank year from the official fact sheet before rendering.
- Military #4: data updated to 2025 (SIPRI fact sheets). 2025 is the first year since 1990 in which the next 9 combined outspend the USA. Renders are mil_short_v3.mp4 and NumbersInMotion_Military_Budgets_1990-2025.mp4; thumbnail is mil_thumb_v3.jpg.

- New renderer flags (10 Nov): `--ease 0.35` makes rows snap faster, and names now always sit in their rank slot. For fast-moving data (exchange-rate swings), subsample to 2-year steps.
- Check that any "X was #1" claim holds with full coverage. For example, Kuwait's data starts in 1962 and Qatar's and the UAE's in 1970, so the GDP-per-capita claim starts at 1970.


## Format rotation (decided by Ahmed, 10 Nov 2026) — MANDATORY
The channel no longer makes only bar chart races. Every new topic uses a **different idea from the last one**, in the
**paper/sticker look** (`--theme paper` in render_v2.py; formats.py always uses it). Rotate in this order and add new
ideas to the list when you have them:

| Turn | Format | Tool | Status |
|---|---|---|---|
| #5 | **Quiz: "Who ___ more?"** two countries, timer, reveal, score | `formats.py quiz` | CO₂ 2024, rendered 10 Nov, awaiting Ahmed's OK to upload |
| #6 | **Knockout: "Last Country Standing"** threshold rises, countries fall out | `formats.py knockout` | sample only (military 2025); needs a long (horizontal) version |
| #7+ | New idea each time: countryball sprint race, real-size zoom-out, "X = how many Y" stacking, or the classic bar race in paper theme | to build | |

Rules for every format:
- Frame 0 must already show the question and something to look at (no slide-in, no blink on the first frame).
- Everything must be readable on mute. Shorts 18–25 s. Long videos get `--endcard 14`.
- Each topic ships: 1 long (horizontal), 1 Short (vertical), 1 thumbnail, 1 metadata txt. Upload as Private; Ahmed publishes or OKs.
- Never state a made-up stat (no "90% fail"). Skip quiz pairs closer than about 5% (data revisions could flip them).
- After each topic, compare the Short's "stayed to watch" with earlier formats here:
  population 48.4% · GDP 52.1% · military v3 54.0% (AVD 0:20/0:22) · gdppc v3 (published 10 Nov, check).

Quiz commands (CO₂ example; csv columns: entity,total,pc):
```
python3 formats.py quiz --csv data/co2_2024.csv --year 2024 --topic "CO₂ emissions" --rounds short --out out/co2_quiz_short.mp4
python3 formats.py quiz --csv data/co2_2024.csv --year 2024 --topic "CO₂ emissions" --rounds long --horizontal --endcard 14 --out out/x.mp4
python3 formats.py thumb --csv data/co2_2024.csv --out out/co2_thumb.jpg
```
Round lists (SHORT_ROUNDS, LONG_ROUNDS), the verb ("POLLUTES") and thumbnail text are set in formats.py; edit them per topic.
CO₂ data: Our World in Data co2-data (GitHub raw), year 2024, countries over 1M people. 2025 values there are projections, so they were not used.
