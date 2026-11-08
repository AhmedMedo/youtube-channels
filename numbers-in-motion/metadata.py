"""Generate YouTube title / description / tags for a rendered data video.

Usage:
    python metadata.py --csv data/population.csv --topic "Most Populous Countries" \
        --unit "people" --source "Gapminder (gapminder.org)" --top 10 --out out/population_meta.txt
"""
import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--unit", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    df = pd.read_csv(a.csv)
    y0, y1 = int(df.year.min()), int(df.year.max())
    first = df[df.year == y0].nlargest(a.top, "value")
    last = df[df.year == y1].nlargest(a.top, "value")
    leader0, leader1 = first.iloc[0].entity, last.iloc[0].entity
    newcomers = [e for e in last.entity if e not in set(first.entity)]
    dropped = [e for e in first.entity if e not in set(last.entity)]

    titles = [
        f"{a.topic} {y0}–{y1} | Top {a.top} Every Year",
        f"How {leader1} Became #1: {a.topic} ({y0}–{y1})",
        f"{a.topic} Ranked: {y1 - y0} Years in {len(df.year.unique())} Steps",
    ]
    desc = f"""{a.topic} from {y0} to {y1}, animated as a racing bar chart.

In {y0} the leader was {leader0}. By {y1} it was {leader1}.
Entered the top {a.top}: {', '.join(newcomers) or 'none'}.
Dropped out of the top {a.top}: {', '.join(dropped) or 'none'}.

Final top {a.top} ({y1}):
""" + "\n".join(
        f"{i + 1}. {r.entity} — {r.value:,.0f} {a.unit}".rstrip()
        for i, r in enumerate(last.itertuples())
    ) + f"""

Data source: {a.source}
Chart, animation and editing: original work produced for this channel.

#data #statistics #ranking #history #{a.topic.replace(' ', '').lower()}
"""
    tags = [
        a.topic.lower(), "data visualization", "racing bar chart", "statistics",
        "ranking", f"{y0} to {y1}", "animated chart", "top 10",
    ] + [e.lower() for e in last.entity.head(5)]

    text = "TITLE OPTIONS\n" + "\n".join(f"- {t}" for t in titles)
    text += "\n\nDESCRIPTION\n" + desc + "\nTAGS\n" + ", ".join(tags) + "\n"
    if a.out:
        open(a.out, "w").write(text)
        print(f"wrote {a.out}")
    print(text)


if __name__ == "__main__":
    main()
