"""Episode plan + YouTube metadata for the sleep channel (v2, Nov 2026).

    python metadata.py 3     → JSON recipe for episode 3 (render flags, title, description, tags, promo copy)

v2 rules (from the Nov 10 analytics + research): the TITLE is the search query (use + length first, brand last),
poetic names live in the description only, the thumbnail carries ONE big keyword + hours badge, and scenes are
specific cozy places. Episode number → deterministic recipe, so no two episodes share music or scene.
"""
import json
import sys

CHANNEL = "Driftlight"

# theme rotation starts at episode 3 (episodes 1–2 were published with the v1 format, see episodes.md)
THEMES = [
    dict(scene="rain_window", mood="rain", rain=0.8, name="Rain for Deep Sleep", big="RAIN", sub="for deep sleep",
         title="Rain Sounds for Sleeping 🌧️ {h} of Soft Rain & Calm Music | Cozy Window Ambience",
         lead="soft rain on a cozy window with slow, original ambient music underneath",
         tags=["rain sounds for sleeping", "rain sounds", "rain and music", "cozy ambience", "rain on window"],
         hash="#rainsounds #sleepmusic #cozyambience #deepsleep"),
    dict(scene="night_sky", mood="night", rain=None, name="Deep Sleep Under the Stars", big="DEEP|SLEEP", sub="calm night music",
         title="Deep Sleep Music 🌙 {h} of Calm Ambient Music to Fall Asleep Fast | Starry Night",
         lead="slow, warm ambient music under a drifting starry sky",
         tags=["deep sleep music", "fall asleep fast", "calm music", "starry night", "night ambience"],
         hash="#deepsleep #sleepmusic #ambient #relaxingmusic"),
    dict(scene="rain_window", mood="rain", rain=1.0, name="Rainy Night Study", big="RAINY|NIGHT", sub="study & relax",
         title="Rainy Night Ambience ☔ {h} of Rain & Soft Music for Studying, Reading & Relaxing",
         lead="steady rain at the window and gentle ambient music for studying, reading or winding down",
         tags=["rainy night", "study music", "rain ambience", "music for reading", "focus music"],
         hash="#rainynight #studymusic #rainsounds #relax"),
    dict(scene="night_sky", mood="ocean", rain=None, name="Stress Relief by the Lake", big="CALM", sub="stress relief music",
         title="Relaxing Music for Stress Relief ✨ {h} of Calm Ambient Music | Quiet Night Lake",
         lead="calm, spacious ambient music over a quiet night lake",
         tags=["stress relief music", "relaxing music", "calming music", "anxiety relief", "meditation music"],
         hash="#stressrelief #relaxingmusic #calm #ambient"),
]
HOURS = [2, 3, 2, 3, 2, 3, 2, 3]          # delivery cap is 400 MiB/file; 3 h needs crf 33+ (see PLAYBOOK)
KEYS = [2, -3, 1, -1, 0, -2]


def plan(ep: int) -> dict:
    i = max(0, ep - 3)
    th = THEMES[i % len(THEMES)]
    hours = HOURS[i % len(HOURS)]
    seed, key = 1000 + ep * 7, KEYS[i % len(KEYS)]
    h = f"{hours} Hour" + ("s" if hours > 1 else "")
    title = th["title"].format(h=h)
    desc = (
        f"{h} of {th['lead']} — made for deep sleep, study and quiet focus.\n\n"
        f"\"{th['name']}\" is episode {ep:03d} of {CHANNEL}. Everything here is original and made by us: the music is "
        "generated note by note for this episode and the scene is drawn for it. No reused loops, no samples, "
        "no copyrighted material.\n\n"
        "Tips: low volume, dim the screen, set a sleep timer. Prefer a dark screen? A black-screen version is on the channel.\n\n"
        f"{th['hash']}"
    )
    tags = th["tags"] + ["sleep music", "ambient music", "relaxing music", "deep sleep", f"{hours} hour sleep music",
                         "music for sleeping", "driftlight"]
    render_args = (f"--scene {th['scene']} --seed {seed} --mood {th['mood']} --key {key} --duration {hours * 3600} "
                   f"--loop 180 --fps 24 --title \"{th['name']}\" --thumb-big \"{th['big']}\" --thumb-sub \"{th['sub']}\""
                   + (f" --rain {th['rain']}" if th["rain"] is not None else ""))
    return dict(
        episode=ep, scene=th["scene"], mood=th["mood"], seed=seed, key=key, hours=hours, duration=hours * 3600,
        render_args=render_args, title=title, short_title=th["name"], thumb_big=th["big"], thumb_sub=th["sub"],
        subtitle=th["sub"], description=desc, tags=tags,
        short_title_yt=f"{th['big'].replace('|', ' ').title()} to fall asleep 💤 #sleepmusic #shorts",
        blackscreen_title=f"{title.split(h)[0].strip()[:-1].strip()} — {h} BLACK SCREEN | Dark Screen Sleep Music",
        privacy="private", made_for_kids=False, category="Music", ai_altered="No (procedural synthesis, owner's decision)",
    )


if __name__ == "__main__":
    print(json.dumps(plan(int(sys.argv[1]) if len(sys.argv) > 1 else 3), indent=2, ensure_ascii=False))
