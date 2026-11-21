# Numbers in Motion — Playbook

You are the production team for the faceless YouTube channel **Numbers in Motion** (@NumbersInMotionTV).
Owner: Ahmed (Cairo, GMT+2). He writes in Egyptian Arabic — reply to him in Egyptian Arabic, short and clear.
He is busy and dislikes slow polishing loops: ship good-enough fast, flag issues in one line.

## Scheduled runs: OFF (21 Nov 2026, Ahmed)
Ahmed cancelled all scheduled tasks and runs the channel manually from chat. Ep 2 (Power edition, winner Sweden) was built 18 Nov and is the 21 Nov upload.

## Where finished episodes go (Ahmed, 21 Nov 2026)
Every finished episode goes to Ahmed's Mac: `~/Documents/Number of Motions/<YYYY-MM-DD> - <short title>/` with
`long.mp4`, `short.mp4`, `thumbnail.jpg`, `metadata.txt` (titles, descriptions, settings). Date = publish date.
Write with device_commit_files (use the SendUserFile fileUuid for files over ~50 MB). Ask for ~/Documents access if needed.
Not on the Mac (rendered by older team runs, files gone): Most Populous 1952–2007, USA vs China economy,
Richest per Person long, Internet knockout #6.

## Subscriber push (Ahmed, 21 Nov 2026)
Every episode from ep 3 on: animated SUBSCRIBE button + "to see who wins the next episode!" after the crown (long, built
into `lcs.py`), and a SUBSCRIBE button on the Short's end card. Titles end with "Ep N" (ep 1 and 2 titles updated 21 Nov).

## Direction (decided 14 Nov 2026 by Ahmed): Last Country Standing 2.0
Every new long video is a **Last Country Standing 2.0** episode (`lcs.py`, rounds built in `lcs_data.py`): all 193 UN
countries, 10 rule rounds on real sourced numbers, A→Z grid, closest-call card, crown, comment CTA. Each episode is a
distinct concept (different rules/data, different winner) — never re-run the same rule set. Each also ships one Short
(the round with the biggest names eliminated) and a bright thumbnail. The "Planned slots" topics below are superseded
unless they can be turned into rounds. Background evidence: `RESEARCH_2026-11-14.md`.

First result (ep 1, 15 Nov, ~28 h): long **1K views, 5 likes, 4 comments** (a French viewer replied to the CTA) vs
5–65 views for every earlier long; channel 28-day watch time 21.3 h → 51.4 h. The Short got only 171 views (earlier
knockout Short got 1.4K) — the long is now the engine, the Short is secondary. Judge the format after 6 episodes.

Ep 1 after 7 days (21 Nov): 1.1K views, CTR 6.9% on 11.9K impressions (was ~1.5%), avg view 2:35 = 44% (was 0:23–0:50),
44.7 h watch time, +3 subs, 76% of views from Browse (home feed). 48-h views down to 108, i.e. a single video decays in
about a week: the lever now is steady new episodes. Channel 28 days: 8.2K views, 66.9 h, 8 subs. 99% new viewers.

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
| 3b | Richest per person Short v3 (1970–2024, 2-year steps) | links to k_mEu5f5vz0 | shorts/Ik1gzJl2umY (public 10 Nov) |
| 5 | Who Pollutes More? CO₂ quiz 2024 | youtu.be/Clrd3W518lQ (public 10 Nov) | shorts/OXn1Nw7SF6s (public 10 Nov) |
| 6 | Last Country Standing: internet users 2024 (knockout) | youtu.be/g1OQNLHnK5k (public since 11–12 Nov; 5 views by 13 Nov) | shorts/M8v36J-ut-4 (public; 1,437 views, 61% stayed, 90% avg viewed by 13 Nov) |

## How work is scheduled (changed 14 Nov 2026, by Ahmed)
The two midweek teams (Sun+Wed for this channel, Mon+Thu for Driftlight) are **paused, not deleted** —
they can be switched back on. Everything now happens in **one Saturday batch** so Ahmed can watch it happen:

| Run | Cairo time | What it does |
|---|---|---|
| Saturday studio — Numbers in Motion | Sat 11:23 | fills every empty Tue/Sat 22:00 slot in the next 14 days |
| Saturday studio — Driftlight | Sat 14:41 | renders 2 sleep episodes; Ahmed uploads them himself |

**Two weeks ahead, not more.** The first run builds four videos because the buffer is empty; after that
it is usually two, since only two new slots enter the 14-day window each week. Do not build past that
window to "get ahead" — unpublished stock goes stale and the format keeps changing.

**Slot rule:** before producing, check YouTube Studio (Content tab, scheduled items) and the table above.
Skip any slot that already has a scheduled or published long video. Never two long videos on the same day,
and never two Shorts on the same day.

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
| #5 | **Quiz: "Who ___ more?"** two countries, timer, reveal, score | `formats.py quiz` | CO₂ 2024 — PUBLIC 10 Nov: long youtu.be/Clrd3W518lQ · Short youtube.com/shorts/OXn1Nw7SF6s |
| #6 | **Knockout: "Last Country Standing"** threshold rises, countries fall out | `formats.py knockout` (`--horizontal --n 40 --endcard 14` long ≈2:58; `--n 12` Short ≈21.6 s; `kothumb`) | Internet users 2024 — uploaded Private 11 Nov (long g1OQNLHnK5k, Short M8v36J-ut-4) |
| #7 | **Last Country Standing 2.0**: all 193 UN countries, 10 rule rounds, A→Z grid, closest-call card, crown | `lcs.py long / short --rounds N / thumb`, rounds in `lcs_data.py` → `data/lcs/ep1.json` | Ep 1 (winner France) — both PUBLIC 14 Nov: long PFQKL0aP6C4 (chapters, sources, end screen from 5:38, playlist), Short LJPX2OttO1U (related video → long). Long files are too big for Chrome upload (AV1 720p still 5.4 MB): Ahmed drags the file into Studio, Claude fills the rest |
| #8+ | New idea each time: countryball sprint race, real-size zoom-out, "X = how many Y" stacking, or the classic bar race in paper theme | to build | |

Rules for every format:
- Frame 0 must already show the question and something to look at (no slide-in, no blink on the first frame).
- Everything must be readable on mute. Shorts 18–25 s. Long videos get `--endcard 14`.
- Each topic ships: 1 long (horizontal), 1 Short (vertical), 1 thumbnail, 1 metadata txt. Upload as Private unless Ahmed says otherwise.
- Browser upload limit is 3.8 MB per call, so re-encode before uploading: `-crf 26` for a Short, up to `-crf 33` for a long video (flat graphics survive it).
- Before switching a video to Public, wait for "Checks complete. No issues found." YouTube warns that publishing during the check risks a strike or restricted visibility.
- Link the Short to its long video with Related video after both are up.
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

## Playlists (created 10 Nov 2026)
- **Bar Chart Races** — https://www.youtube.com/playlist?list=PLFv3MyGofp78 (military, richest per person, USA vs China, population)
- **Country Quizzes** — https://www.youtube.com/playlist?list=PLTuyb-nBcJow (CO₂ quiz)
- **Last Country Standing** — https://www.youtube.com/playlist?list=PLQCm9t3k2PRI (internet users; created 11 Nov)

**Only these 3 playlists (Ahmed, 11 Nov 2026).** Do NOT create new playlists without his OK; a new format goes into the closest of the three
(races → Bar Chart Races, quiz-style → Country Quizzes, knockouts → Last Country Standing).

Every new long video goes into the playlist for its format, and its description ends with
`More races: <link>` or `More quizzes: <link>`. The point is autoplay: a viewer who finishes one
video keeps going through the playlist, which is what grows watch hours toward the 4,000 the YPP needs.
Studio flow: Content → Videos → tick the videos → Add to playlist → New playlist (or an existing one) → Save.
The `/playlists` Studio URL 404s; reach them from Content → Playlists.

## Shorts performance log + publishing rate (10 Nov 2026)
"Stayed to watch" per Short, from YouTube Studio (Engagement → How viewers engaged):

| Short | Stayed | AVD | Views | Note |
|---|---|---|---|---|
| Most populous (v1) | 48.4% | 0:21 / 0:30 | ~1,100 | |
| GDP / USA vs China (v1) | 52.1% | 0:27 / 0:42 | ~1,250 | |
| Military v3 (bar race, paper hook) | **54.0%** | 0:20 / 0:22 | 1,256 | best so far |
| Richest per person v3 (bar race) | **16.4%** | 0:18 / 0:21 | 125 | died; 10 near-equal bars, nothing to look at in frame 1 |
| CO₂ quiz (quiz format) | 100% (2 engaged views — meaningless) | 0:40 | 5 | published 10 Nov ~20:45; got almost no seed views |

Lessons:
- A race only works when ONE bar dominates or the lead actually changes. Ten similar bars = an instant swipe.
- **One Short per day, maximum.** Three went out on 10 Nov; the third got no seed views for hours. Space them out, and never publish a Short right after one that scored under ~40%.
- Check "stayed to watch" for the previous Short before publishing the next one, and record it in this table.

### The CO₂ quiz Short got 6 views — what that tells us (12 Nov)
Everyone who saw it watched it: 100% stayed to watch, and an average view duration of 0:28 on a
0:21 Short, which means replays. YouTube simply never showed it — 6 views, and the Shorts feed was
still 83% of them. So the format was not rejected by viewers; it got no impressions.
The one thing that stands out: it was the **third Short published that day**. Nothing else about it
differs from the Shorts that did get seeded. Treat the one-per-day rule as the main suspect and keep
to it. Do not re-upload the same Short; make a new one on the topic if it's worth another try.

### What is working (12 Nov)
Knockout > bar race > quiz, on the evidence so far. 61% on the knockout against 54% on the best bar
race. Knockout and quiz both have a question the viewer waits to see answered; the knockout also has
something moving in every second. Keep rotating, but weight the rotation toward knockout.

## Knockout: internet users (11 Nov 2026)
- Data: `data/internet_users_2024.csv` = WB IT.NET.USER.ZS (ITU) × SP.POP.TOTL, 2024, countries ≥1M people with 2024 data
  (missing: Myanmar, Sudan, Yemen, N. Korea, Syria…). Raw bulk files (release 2026-07-13) from GitHub mirrors; 3 mirror copies
  identical, population matches the 2026-10-08 release. CNNIC says China ≈1.1B (ITU higher) — noted in the description.
- Payoff "China > USA+Indonesia+Brazil+Pakistan+Russia combined" (1.30B vs 0.99B) holds even with CNNIC's figure.
- Long 1080p crf 33 was 8.7 MB; uploaded a 720p two-pass 120 kbps version (3.5 MB, still clean). Short 1.9 MB.
- Studio: pressing Escape after a hashtag inside the UPLOAD dialog closes the whole dialog (draft survives; reopen via Edit draft). Put hashtags last or add them on the edit page. Ctrl+End does not reach the description end — click after the last line.
- Chrome: Ahmed's main Chrome is **Browser 1** (deviceId 5b24f15f-4337-4e7b-8c4d-d1dc2ab199b8) → select_browser it directly.
- Knockout is a new format → needs its own playlist ("Last Country Standing").
- Next in rotation (#7): new idea (sprint race / zoom-out / stacking) or paper-theme bar race.

## Planned slots (set 14 Nov 2026) — and why the playlists are NOT a quota
Live calendar (Ahmed's): https://claude.ai/artifact/5woiayfnQ3J82UXTxQCbgZ

A playlist is a container, not a target. Do **not** try to ship one video per playlist per cycle:
the channel has 4 subscribers and the formats are not equal — knockout 61% stayed-to-watch against
54% for the best bar race. Lead with what works and let each playlist fill at its own pace.
Rotation stays, but weighted: **knockout roughly every other slot** until something beats it.

| Publish (22:00 Cairo) | Topic | Format | Playlist | Prep run |
|---|---|---|---|---|
| Sat 14 Nov | — nothing prepared, slot lost | — | — | no run happened |
| Tue 17 Nov | — nothing prepared, slot lost | — | — | first batch is Sat 21 |
| Sat 21 Nov | Life expectancy | Knockout | Last Country Standing | Sat 21 Nov 11:23 |
| Tue 24 Nov | Most visited countries (tourism) | Bar race (paper) | Bar Chart Races | Sat 21 Nov 11:23 |
| Sat 28 Nov | Biggest cities | Knockout | Last Country Standing | Sat 21 Nov 11:23 |
| Tue 1 Dec | Football World Cup wins | Quiz | Country Quizzes | Sat 21 Nov 11:23 |
| Sat 5 Dec | Billionaires by country | Knockout | Last Country Standing | Sat 28 Nov 11:23 |

Everything shifted one slot later than the 14 Nov plan: pausing the midweek teams left Sat 14 and
Tue 17 Nov with nothing built, so the first Saturday batch (21 Nov) picks the list up from the top.

Why these pairings: tourism earns a bar race because France dominates the #1 spot and 2020 gives a
collapse worth watching; life expectancy, biggest cities and billionaires all have a single winner
worth waiting for, which is what knockout is for; World Cup wins is a small set of discrete numbers,
which is quiz material and gives the quiz the fair solo-day test it never got on 10 Nov.

Each slot ships one long plus one Short, and the Short is the only Short that day.

**Long-video length — superseded by the notice at the top of this file (14 Nov).** "Channel facts"
says 8–12 minutes; everything shipped since 10 Nov is about 3 minutes. The research settles the
direction of travel: every current hit in the niche is 6–17 minutes, and our own retention curve
is flat after the first 35 seconds, so length pays once the opening holds. The exact target waits
for Ahmed's decision; do not build 3-minute videos from the table above in the meantime.
