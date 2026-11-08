"""Episode plan + YouTube metadata for the sleep channel.

    python metadata.py 1            → prints JSON for episode 1 (scene, mood, seed, duration, title, description, tags)

Episode number → deterministic recipe, so every scheduled run produces a *different* video (different
seed = different stars/moon/mountains and different music) and never re-uploads the same loop.
"""
import json
import sys

CHANNEL = "Driftlight"  # overwrite with the chosen name

# rotate through scenes / moods / lengths; add scenes here as render_scene.py gains them
SCENES = ["night_sky"]
MOODS = ["night", "rain", "ocean"]
HOURS = [1, 2, 1, 3, 2, 1, 4, 2, 1, 8]

TITLES = {
    "night": ["Starlight Drift", "Under a Quiet Sky", "Moonlit Hours", "Slow Stars", "Night Without Clocks"],
    "rain": ["Rain on the Window", "Soft Rain, Deep Sleep", "Grey Afternoon Rain", "Rain for Sleeping"],
    "ocean": ["Tide at Midnight", "Slow Waves", "The Sea Breathes", "Ocean Night"],
}


def plan(ep: int) -> dict:
    scene = SCENES[(ep - 1) % len(SCENES)]
    mood = MOODS[(ep - 1) % len(MOODS)]
    hours = HOURS[(ep - 1) % len(HOURS)]
    seed = 1000 + ep * 7
    key = [0, -2, 2, -3, 1, -1][(ep - 1) % 6]
    name = TITLES[mood][(ep - 1) // len(MOODS) % len(TITLES[mood])]
    h = f"{hours} Hour" + ("s" if hours > 1 else "")
    title = f"{name} — {h} of Original Ambient Sleep Music | {CHANNEL}"
    desc = (
        f"{name}: {h.lower()} of slow, original ambient music composed for deep sleep, study and quiet focus.\n\n"
        "Everything in this video is original and made by us — the music is generated note by note for this episode, "
        "and the scene is drawn for it. No loops reused from other videos, no samples, no copyrighted material.\n\n"
        "Tips: play at low volume, turn screen brightness down, and set a sleep timer.\n\n"
        f"Episode {ep:03d} · {CHANNEL}\n"
        "#sleepmusic #ambient #relaxingmusic #deepsleep #studymusic"
    )
    tags = ["sleep music", "ambient music", "relaxing music", "deep sleep", "calm music", "study music",
            "music for sleeping", f"{hours} hour sleep music", "original ambient", "night ambience",
            {"night": "starry night", "rain": "rain sounds", "ocean": "ocean waves"}[mood]]
    return dict(episode=ep, scene=scene, mood=mood, seed=seed, key=key, hours=hours, duration=hours * 3600,
                title=title, short_title=name, subtitle=f"{h} · Original Sleep Music", description=desc, tags=tags,
                privacy="private", made_for_kids=False, category="Music")


if __name__ == "__main__":
    print(json.dumps(plan(int(sys.argv[1]) if len(sys.argv) > 1 else 1), indent=2, ensure_ascii=False))
