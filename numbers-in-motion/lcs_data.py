#!/usr/bin/env python3
"""Build the rounds for "Last Country Standing" episodes from data/lcs/base2.csv.
Usage: python3 lcs_data.py ep2   → writes data/lcs/ep2.json: countries, and per round the rule, source, who goes out (with values)."""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = pd.read_csv(os.path.join(HERE, "data/lcs/base3.csv"))
D = D[D.name != "Vatican City"].set_index("name")            # 193 UN member states
WORLD = D
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


EP1 = [  # (title line, detail, source, column, out-test, value formatter, closest-call side)
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


def lat(v):
    return f"{abs(v):.0f}°{'S' if v < 0 else 'N'}" if round(abs(v)) else "0° (on the line)"


EP2 = [
    ("Centre is south of", "the equator → OUT", "Country centre point · mledoze/countries dataset", "lat",
     lambda r: r["lat"] < 0, lat, "min"),
    ("Smaller than 20,000 km²", "→ OUT", "Land area · mledoze/countries dataset", "area",
     lambda r: r["area"] < 2e4, lambda v: f"{v:,.0f} km²", "min"),
    ("Under 20% of electricity", "from renewables → OUT", "Ember & Energy Institute · via Our World in Data · latest year",
     "renewables_share_elec", lambda r: not (r["renewables_share_elec"] >= 20), lambda v: f"{v:.1f}% renewable", "min"),
    ("Under 2,000 kWh of", "electricity per person → OUT", "Ember & Energy Institute · via Our World in Data · latest year",
     "per_capita_electricity", lambda r: r["per_capita_electricity"] < 2000, lambda v: f"{v:,.0f} kWh", "min"),
    ("Fewer than 10 million", "people → OUT", "UN World Population Prospects 2024 · via Our World in Data", "pop",
     lambda r: r["pop"] < 10e6, f_pop, "min"),
    ("Fewer than 2", "land neighbours → OUT", "Land borders · mledoze/countries dataset", "borders",
     lambda r: r["borders"] < 2, lambda v: f"{int(v)} neighbour" + ("" if v == 1 else "s"), "min"),
    ("No nuclear power", "→ OUT", "Ember & Energy Institute · via Our World in Data · latest year", "nuclear_share_elec",
     lambda r: not (r["nuclear_share_elec"] > 0), lambda v: f"{v:.0f}% nuclear", "min"),
    ("Bigger than 1 million km²", "→ OUT", "Land area · mledoze/countries dataset", "area",
     lambda r: r["area"] > 1e6, lambda v: f"{v / 1e6:.1f}M km²", "max"),
    ("Under 50% of electricity", "from renewables → OUT", "Ember & Energy Institute · via Our World in Data · latest year",
     "renewables_share_elec", lambda r: not (r["renewables_share_elec"] >= 50), lambda v: f"{v:.1f}% renewable", "min"),
    ("FINAL: least electricity", "per person → OUT", "Ember & Energy Institute · via Our World in Data · latest year",
     "per_capita_electricity", lambda r: r["per_capita_electricity"] < 10000, lambda v: f"{v:,.0f} kWh", None),
]


SAME_CAP = {"Andorra", "Djibouti", "Kuwait", "Luxembourg", "Monaco", "Singapore", "San Marino", "Guatemala", "Mexico", "Panama"}
EP3 = [
    ("Centre is west of", "Greenwich (0°) → OUT", "Country centre point · mledoze/countries dataset", "lng",
     lambda r: r["lng"] < 0, lambda v: f"{abs(v):.0f}°{'W' if v < 0 else 'E'}", "min"),
    ("Capital has the same", "name as the country → OUT", "Capital cities · mledoze/countries dataset", "capital",
     lambda r: r.name in SAME_CAP, lambda v: str(v), None),
    ("Smaller than 50,000 km²", "→ OUT", "Land area · mledoze/countries dataset", "area",
     lambda r: r["area"] < 5e4, lambda v: f"{v:,.0f} km²", "min"),
    ("Uses the euro €", "→ OUT", "Currencies · mledoze/countries dataset", "euro",
     lambda r: bool(r["euro"]), lambda v: "uses €", None),
    ("More than 300 people", "per km² → OUT", "UN population 2024 ÷ land area · OWID & mledoze", "density",
     lambda r: r["density"] > 300, lambda v: f"{v:,.0f} per km²", "max"),
    ("Fewer than 20 million", "people → OUT", "UN World Population Prospects 2024 · via Our World in Data", "pop",
     lambda r: r["pop"] < 20e6, f_pop, "min"),
    ("Fewer than 5", "land neighbours → OUT", "Land borders · mledoze/countries dataset", "borders",
     lambda r: r["borders"] < 5, lambda v: f"{int(v)} neighbour" + ("" if v == 1 else "s"), "min"),
    ("Smaller than", "1 million km² → OUT", "Land area · mledoze/countries dataset", "area",
     lambda r: r["area"] < 1e6, lambda v: f"{v / 1e6:.2f}M km²", "min"),
    ("Under 50% of people", "online → OUT", "World Bank / ITU · latest year available", "net",
     lambda r: not (r["net"] >= 50), lambda v: f"{v:.0f}% online", "min"),
    ("FINAL: more CO₂", "per person → OUT", "Global Carbon Budget · 2024 · via Our World in Data", "co2pc",
     lambda r: r["co2pc"] > 4.5, lambda v: f"{v:.1f} t CO₂ per person", None),
]

# ---- Episode 4: the 50 US states (data/lcs/us_base.csv, built 21 Nov 2026)
# pop/base20/dom: U.S. Census Bureau Vintage 2025 estimates (NST-EST2025-ALLDATA.csv; base20 = April 1 2020 estimates base,
# dom = net domestic migration July 2024 – July 2025). land_sqmi: Census TIGER ALAND. high_ft: USGS "Elevations and
# Distances in the United States". tz: 49 CFR Part 71. year: year of statehood.
US = pd.read_csv(os.path.join(HERE, "data/lcs/us_base.csv")).set_index("name")


def f_pop2(v):
    return f"{v / 1e6:.2f}M people" if v >= 1e6 else f"{v / 1e3:.0f}K people"


EP4 = [
    ("Fewer people than", "in 2020 → OUT", "U.S. Census Bureau · Vintage 2025 population estimates", "chg",
     lambda r: r["chg"] < 0, lambda v: f"{int(v):+,} people", "min"),
    ("Smaller than", "9,500 sq mi → OUT", "Land area · U.S. Census Bureau", "land_sqmi",
     lambda r: r["land_sqmi"] < 9500, lambda v: f"{int(v):,} sq mi", "min"),
    ("Fewer than 2 million", "people → OUT", "U.S. Census Bureau · Vintage 2025 population estimates", "pop",
     lambda r: r["pop"] < 2e6, f_pop2, "min"),
    ("More people moved out", "than moved in → OUT", "U.S. Census Bureau · moves between states, July 2024 – July 2025", "dom",
     lambda r: r["dom"] < 0, lambda v: f"net {int(v):+,}", "min"),
    ("Became a state", "before 1800 → OUT", "Year each state joined the Union", "year",
     lambda r: r["year"] < 1800, lambda v: f"state since {int(v)}", "min"),
    ("Highest point is under", "2,000 ft → OUT", "U.S. Geological Survey · Elevations and Distances in the U.S.", "high_ft",
     lambda r: r["high_ft"] < 2000, lambda v: f"{int(v):,} ft", "min"),
    ("Smaller than", "80,000 sq mi → OUT", "Land area · U.S. Census Bureau", "land_sqmi",
     lambda r: r["land_sqmi"] < 80000, lambda v: f"{int(v):,} sq mi", "min"),
    ("Borders California", "→ OUT", "State borders · U.S. Census Bureau", "borders_ca",
     lambda r: bool(r["borders_ca"]), lambda v: "borders California", None),
    ("Only ONE", "time zone → OUT", "U.S. Department of Transportation · 49 CFR Part 71", "tz",
     lambda r: r["tz"] <= 1, lambda v: f"{int(v)} time zone" + ("" if v == 1 else "s"), None),
    ("FINAL: slower growth", "since 2020 → OUT", "U.S. Census Bureau · Vintage 2025 population estimates", "growth",
     lambda r: r["growth"] < 10, lambda v: f"{v:+.1f}% since 2020", None),
]

EPISODES = {
    "ep4": (EP4, {"base": "us", "flag_dir": "us_flags", "unit": ["state", "states"], "total": 50,
                  "brand": ["LAST STATE", "STANDING"], "sticker": 0.66, "teaser": "California & New York are OUT in round 1!",
                  "win_value": "+10.4% people since 2020", "win_note": "Fastest-growing state since 2020",
                  "thumb": [["California", "shocked"], ["Texas", "worried"], ["New York", "worried"]],
                  "thumb_pill": "US STATES EDITION"}),
    "ep1": (EP1, {"teaser": "Even the USA is OUT by round 5!", "win_value": "12 time zones",
                  "win_note": "Thanks to its overseas territories",
                  "thumb": [["United States", "shocked"], ["Egypt", "worried"], ["China", "worried"]]}),
    "ep3": (EP3, {"teaser": "The USA & Brazil are OUT in round 1!", "win_value": None,
                  "win_note": "Least CO₂ per person in the final",
                  "thumb": [["United States", "shocked"], ["China", "worried"], ["Brazil", "shocked"]], "thumb_pill": "MAP EDITION"}),
    "ep2": (EP2, {"teaser": "China & the USA don't make the final 3!", "win_value": None,
                  "win_note": "Mostly hydro & nuclear power",
                  "thumb": [["United States", "shocked"], ["Germany", "worried"], ["Japan", "worried"]], "thumb_pill": "POWER EDITION"}),
}


def build(ep="ep1"):
    ROUNDS, meta = EPISODES[ep]
    D = US if meta.get("base") == "us" else WORLD
    code = "code" if meta.get("base") == "us" else "cca2"
    alive = sorted(D.index, key=lambda n: NAMES.get(n, n))
    out = {"countries": [{"name": n, "label": NAMES.get(n, n), "cca2": D.loc[n, code]} for n in alive], "rounds": []}
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
    out["meta"] = meta
    if len(alive) == 1:
        out["winner"] = {"name": alive[0], "value": fmt(D.loc[alive[0], col]) + (" per person" if col == "per_capita_electricity" else "")}
    print("alive:", alive)
    json.dump(out, open(os.path.join(HERE, f"data/lcs/{ep}.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else "ep1")
