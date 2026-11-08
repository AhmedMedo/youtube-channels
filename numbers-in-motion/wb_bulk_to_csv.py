"""Convert a World Bank bulk CSV (API_<CODE>_DS2_en_csv_v2_*.csv) to tidy entity,group,year,value.
Keeps sovereign countries only (pycountry match), drops aggregates/territories, keeps entities that ever reach top N."""
import sys, csv, pycountry, pandas as pd
src, out = sys.argv[1], sys.argv[2]
top = int(sys.argv[3]) if len(sys.argv) > 3 else 15
TERR = {"HKG", "MAC", "BMU", "PRI", "GRL", "CYM", "GUM", "VIR", "ABW", "CUW", "SXM", "NCL", "PYF", "FRO", "IMN", "CHI", "GIB", "TCA", "MAF", "ASM", "MNP", "XKX", "PSE"}
CONT = {"AF": "Africa", "AS": "Asia", "EU": "Europe", "NA": "Americas", "SA": "Americas", "OC": "Oceania"}
MIDEAST = {"SAU", "IRN", "IRQ", "ISR", "ARE", "KWT", "QAT", "OMN", "TUR", "SYR", "JOR", "EGY", "YEM", "LBY", "DZA"}
NAME = {"Korea, Rep.": "South Korea", "Iran, Islamic Rep.": "Iran", "Russian Federation": "Russia", "Egypt, Arab Rep.": "Egypt",
        "Turkiye": "Turkey", "Venezuela, RB": "Venezuela", "Syrian Arab Republic": "Syria", "Viet Nam": "Vietnam", "Czechia": "Czech Republic"}
rows = list(csv.reader(open(src, encoding="utf-8-sig")))
hdr = rows[4]; yrs = [int(h) for h in hdr[4:] if h.strip().isdigit()]
recs = []
for r in rows[5:]:
    if len(r) < 5: continue
    code = r[1]
    if code in TERR: continue
    try: c = pycountry.countries.get(alpha_3=code)
    except Exception: c = None
    if not c: continue
    name = NAME.get(r[0], r[0])
    if code in MIDEAST: grp = "Middle East"
    else:
        import pycountry_convert as pc
        try: grp = CONT[pc.country_alpha2_to_continent_code(c.alpha_2)]
        except KeyError: grp = "Asia"
    for y, v in zip(yrs, r[4:]):
        if v.strip(): recs.append((name, grp, y, float(v)))
df = pd.DataFrame(recs, columns=["entity", "group", "year", "value"])
df["rank"] = df.groupby("year").value.rank(ascending=False)
keep = set(df[df["rank"] <= top].entity)
df = df[df.entity.isin(keep)].drop(columns="rank").sort_values(["entity", "year"])
df["value"] = df.value.round(0).astype("int64")
df.to_csv(out, index=False)
print(len(keep), "entities,", df.year.min(), "-", df.year.max(), "rows", len(df))
