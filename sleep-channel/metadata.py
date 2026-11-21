"""Episode plan + YouTube metadata for the sleep channel (v3, 18 Nov 2026).

    python metadata.py 5     → JSON recipe for episode 5 (render flags, title, description, tags)

v3 — ONE upload per episode, EIGHT hours, a title card that dissolves to black.
Decided by Ahmed on 18 Nov from the first ten days of data: watch time follows length.
1 h → 1.56 watch hours per 1,000 impressions, 2 h → 2.58, 3 h → 2.84 (ep004 alone was 61% of
all channel watch time), and the best yield on the channel was the ep003 black screen at 7.28.
So: length up, screen dark, and nothing else changed at once.

Dropped from v2, because they split the audience or cost more than they returned:
  - the separate black-screen upload (it competed with its own main video)
  - the Short (62% of views, 1% of watch hours, and Shorts hours do not count toward the 8,000)
  - the Pinterest pin
v2 kept: the title is the search query, and the thumbnail is ONE big keyword + an hours badge —
that family measured 2.6% and 2.9% CTR, against 0.5% for the "RAIN" redesign that replaced it.
"""
import json
import sys

CHANNEL = "Driftlight"

# theme rotation starts at episode 3 (episodes 1–2 were published with the v1 format, see episodes.md)
THEMES = [
    dict(scene="rain_window", mood="rain", rain=0.8, name="Rain for Deep Sleep",
         lead="soft rain on a cozy window with slow, original ambient music underneath",
         tags=["rain sounds for sleeping", "rain sounds", "rain and music", "cozy ambience", "rain on window"],
         hash="#rainsounds #sleepmusic #cozyambience #deepsleep",
         variants=[("Rain Sounds for Sleeping 🌧️ {h} of Soft Rain & Calm Music", "RAIN", "for deep sleep"),
                   ("Sleep Through the Night 🌧️ {h} of Gentle Rain & Ambient Music", "SLEEP|ALL NIGHT", "rain & soft music"),
                   ("Awake at 3AM? {h} of Soft Rain to Fall Back Asleep", "AWAKE|AT 3AM", "rain for deep sleep")]),
    dict(scene="night_sky", mood="night", rain=None, name="Deep Sleep Under the Stars",
         lead="slow, warm ambient music under a drifting starry sky",
         tags=["deep sleep music", "fall asleep fast", "calm music", "starry night", "night ambience"],
         hash="#deepsleep #sleepmusic #ambient #relaxingmusic",
         variants=[("Deep Sleep Music 🌙 {h} of Calm Ambient Music to Fall Asleep Fast", "DEEP|SLEEP", "calm night music"),
                   ("Can't Switch Off? {h} of Deep Sleep Music for a Racing Mind", "RACING|MIND", "slow music to switch off"),
                   ("Fall Asleep Under the Stars 🌙 {h} of Slow Ambient Sleep Music", "UNDER|THE STARS", "slow sleep music")]),
    dict(scene="rain_window", mood="rain", rain=1.0, name="Rainy Night Study",
         lead="steady rain at the window and gentle ambient music for studying, reading or winding down",
         tags=["rainy night", "study music", "rain ambience", "music for reading", "focus music"],
         hash="#rainynight #studymusic #rainsounds #relax",
         variants=[("Rainy Night Ambience ☔ {h} of Rain & Soft Music for Studying and Reading", "RAINY|NIGHT", "study & relax"),
                   ("Rain for Focus ☔ {h} of Steady Rain & Quiet Music for Study and Work", "RAIN|FOR FOCUS", "study & deep work"),
                   ("A Rainy Night Indoors ☔ {h} of Rain & Calm Music to Read and Unwind", "RAINY|NIGHT IN", "read & unwind")]),
    dict(scene="night_sky", mood="ocean", rain=None, name="Stress Relief by the Lake",
         lead="calm, spacious ambient music over a quiet night lake",
         tags=["stress relief music", "relaxing music", "calming music", "anxiety relief", "meditation music"],
         hash="#stressrelief #relaxingmusic #calm #ambient",
         variants=[("Relaxing Music for Stress Relief ✨ {h} of Calm Ambient Music", "CALM", "stress relief music"),
                   ("When Everything Feels Too Much — {h} of Calm Music for Stress and Anxiety", "TOO|MUCH", "music for hard days"),
                   ("Quiet an Anxious Mind ✨ {h} of Slow Ambient Music for Deep Rest", "ANXIOUS|MIND", "slow music for rest")]),
]
HOURS = [8]          # 8 h throughout; the picture is a title card, so the file is mostly audio (see PLAYBOOK)
INTRO = 18           # seconds of title card before it dissolves into black
# ep005 is the first 8-hour episode and Ahmed asked for ep004's music, so it takes the night-sky theme
# rather than its turn in the rotation.
# ep005 is the first 8-hour episode: Ahmed asked for ep004's music, so it takes the night-sky theme out of
# turn, and seed/key are the ones its audio was actually rendered with on 18 Nov.
EP_OVERRIDE = {5: dict(theme=1, seed=1052, key=-3)}
KEYS = [2, -3, 1, -1, 0, -2]


def plan(ep: int) -> dict:
    i = max(0, ep - 3)
    ov = EP_OVERRIDE.get(ep, {})
    ti = ov.get("theme", i % len(THEMES))
    th = THEMES[ti]
    # a theme comes round every 4 episodes, so rotate its wording and thumbnail too: no two
    # episodes may share a title or a thumbnail (YouTube's inauthentic-content policy)
    seen = sum(1 for e in range(3, ep) if EP_OVERRIDE.get(e, {}).get("theme", (e - 3) % len(THEMES)) == ti)
    tpl, big, sub = th["variants"][seen % len(th["variants"])]
    hours = HOURS[i % len(HOURS)]
    seed, key = ov.get("seed", 1000 + ep * 7), ov.get("key", KEYS[i % len(KEYS)])
    h = f"{hours} Hour" + ("s" if hours > 1 else "")
    title = tpl.format(h=h) + " | Black Screen"
    assert len(title) <= 100, f"title is {len(title)} chars, YouTube allows 100: {title}"
    desc = (
        f"{h} of {th['lead']} — made for deep sleep, study and quiet focus.\n\n"
        f"\"{th['name']}\" is episode {ep:03d} of {CHANNEL}. Everything here is original and made by us: the music is "
        "generated note by note for this episode. No reused loops, no samples, no copyrighted material.\n\n"
        f"The picture fades into a black screen after about {INTRO} seconds and stays dark for the whole {h.lower()}, "
        "so nothing lights the room while you sleep.\n\n"
        "Tips: low volume, set a sleep timer, and let it run through the night.\n\n"
        f"{th['hash']}"
    )
    tags = th["tags"] + ["sleep music", "ambient music", "relaxing music", "deep sleep", f"{hours} hour sleep music",
                         "music for sleeping", "black screen sleep music", "driftlight"]
    tags = list(dict.fromkeys(tags))        # keep order, drop repeats
    build_cmd = f"python3 build_episode.py {ep}"      # the ONLY build command; see PLAYBOOK
    return dict(
        episode=ep, scene=th["scene"], mood=th["mood"], seed=seed, key=key, hours=hours, duration=hours * 3600,
        build_cmd=build_cmd, title=title, short_title=th["name"], thumb_big=big, thumb_sub=sub,
        subtitle=sub, description=desc, tags=tags, intro=INTRO,
        privacy="private", made_for_kids=False, category="Music",
        ai_altered="Ahmed's call — see PLAYBOOK; the music is synthesised by our own code",
    )


if __name__ == "__main__":
    print(json.dumps(plan(int(sys.argv[1]) if len(sys.argv) > 1 else 3), indent=2, ensure_ascii=False))
