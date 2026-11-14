#!/usr/bin/env python3
"""Build the rounds for "Last Country Standing" episode 1 from data/lcs/base.csv.
Writes data/lcs/ep1.json: countries, and per round the rule, source, who goes out (with values)."""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = pd.read_csv(os.path.join(HERE, "data/lcs/base.csv"))
D = D[D.name != "Vatican City"].set_index("name")            # 193 UN member states
# CIA World Factbook: France has 12 time zones (13 counting its Antarctic claim). Dataset says 13.
D.loc["France", "tz"] = 12
NAMES = {"Türkiye": "Türkiye", "United States": "USA", "United Kingdom": "UK", "Central African Republic": "C. African Rep.",
         "DR Congo": "DR Congo", "Bosnia and Herzegovina": "Bosnia", "Saint Vincent and the Grenadines": "St Vincent",
         "Saint Kitts and Nevis": "St Kitts", "Antigua and Barbuda": "Antigua", "São Tomé and Príncipe": "São Tomé",
         "Trinidad and Tobago": "Trinidad", "United Arab Emirates": "UAE", "Papua New Guinea": "PNG",
         "Equatorial Guinea": "Eq. Guinea", "Marshall Islands": "Marshall Is.", "Solomon Islands": "Solomon Is.",
         "Dominican Republic": "Dominican Rep.", "Republic of the Congo": "Congo", "Saint Lucia": "St Lucia"}


def f_pop(v):
    return f"{v / 1e6:.1f}M people" if v >= 1e6 else f"{v / 1e3:.0f}K people"


ROUNDS = [  # (title line, detail, source, column, out-test, value formatter, closest-call side)
    ("Fewer than 1 million people", "→ OUT", "UN World Population Prospects 2024 · via Our World in Data", "pop",
     lambda r: r["pop"] < 1e6, f_pop, "min"),
    ("No coastline", "(landlocked) → OUT", "mledoze/countries dataset", "landlocked",
     lambda r: bool(r["landlocked"]), lambda v: "landlocked", None),
    ("Smaller than 100,000 km²", "→ OUT", "Land area · mledoze/countries dataset", "area",
     lambda r: r["area"] < 1e5, lambda v: f"{v:,.0f} km²", "min"),
    ("Under 70% of people", "online → OUT", "World Bank / ITU · latest year available", "net",
     lambda r: not (r["net"] >= 70), lambda v: "no data" if v != v else f"{v:.0f}% online", "min"),
    ("Fewer than 3", "land neighbours → OUT", "Land borders · mledoze/countries dataset", "borders",
     lambda r: r["borders"] < 3, lambda v: f"{int(v)} neighbour" + ("" if v == 1 else "s"), "min"),
    ("More than 10 tonnes of", "CO₂ per person → OUT", "Global Carbon Budget · 2024 · via Our World in Data", "co2pc",
     lambda r: r["co2pc"] > 10, lambda v: f"{v:.1f} t per person", "max"),
    ("Fewer than 40 million", "people → OUT", "UN World Population Prospects 2024 · via Our World in Data", "pop",
     lambda r: r["pop"] < 40e6, f_pop, "min"),
    ("Under 85% of people", "online → OUT", "World Bank / ITU · latest year available", "net",
     lambda r: not (r["net"] >= 85), lambda v: f"{v:.0f}% online", "min"),
    ("Fewer than 6", "land neighbours → OUT", "Land borders · mledoze/countries dataset", "borders",
     lambda r: r["borders"] < 6, lambda v: f"{int(v)} neighbours", "min"),
    ("Only ONE", "time zone → OUT", "CIA World Factbook", "tz",
     lambda r: r["tz"] <= 1, lambda v: f"{int(v)} time zone" + ("" if v == 1 else "s"), None),
]


def build():
    alive = sorted(D.index, key=lambda n: NAMES.get(n, n))
    out = {"countries": [{"name": n, "label": NAMES.get(n, n), "cca2": D.loc[n, "cca2"]} for n in alive], "rounds": []}
    for title, detail, src, col, test, fmt, side in ROUNDS:
        rows = [(n, D.loc[n]) for n in alive]
        gone = [(n, r[col]) for n, r in rows if test(r)]
        stay = [(n, r[col]) for n, r in rows if not test(r)]
        asc = side != "max"
        gone.sort(key=lambda x: (x[1] != x[1], x[1]) if not isinstance(x[1], (bool,)) else 0, reverse=not asc)
        close = None
        if side and stay:
            c = (min if side == "min" else max)(stay, key=lambda x: x[1])
            close = {"name": c[0], "value": fmt(c[1])}
        out["rounds"].append({"rule": [title, detail], "source": src,
                              "out": [{"name": n, "value": fmt(v)} for n, v in gone], "close": close})
        alive = [n for n, _ in stay]
        print(f"{title} {detail}: -{len(gone)} -> {len(alive)}   close={close}")
    out["winner"] = {"name": alive[0], "value": f"{int(D.loc[alive[0], 'tz'])} time zones"} if len(alive) == 1 else None
    print("alive:", alive)
    json.dump(out, open(os.path.join(HERE, "data/lcs/ep1.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    build()
