"""Export a tidy CSV (entity, group, year, value) from the gapminder dataset.

Usage:
    python export_gapminder.py pop data/population.csv
    python export_gapminder.py gdpPercap data/gdp_per_capita.csv
    python export_gapminder.py lifeExp data/life_expectancy.csv
"""
import sys
from gapminder import gapminder as g

metric = sys.argv[1] if len(sys.argv) > 1 else "pop"
out = sys.argv[2] if len(sys.argv) > 2 else f"data/{metric}.csv"

df = g[["country", "continent", "year", metric]].rename(
    columns={"country": "entity", "continent": "group", metric: "value"}
)
import os
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
df.to_csv(out, index=False)
print(f"wrote {out}: {len(df)} rows, {df.entity.nunique()} entities, years {df.year.min()}-{df.year.max()}")
