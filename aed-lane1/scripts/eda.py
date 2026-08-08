import json
import pandas as pd

with open("data/scdf_aed_frozen.geojson") as f:
    data = json.load(f)

rows = []
for feat in data["features"]:
    props = feat["properties"]
    lon, lat = feat["geometry"]["coordinates"]
    rows.append({**props, "lon": lon, "lat": lat})

df = pd.DataFrame(rows)
print(f"Total AED records: {len(df)}")
print(df.dtypes)
print(df.head(3))

# Missingness audit
print(df.isnull().sum().sort_values(ascending=False))
print((df["OPERATING_HOURS"].str.strip() == "").sum(), "blank operating hours")

# Operating-hours format survey — this drives Person B's parser design
# Frequency of raw formats — look for pattern families, not just the top one
print(df["OPERATING_HOURS"].value_counts().head(30))

# How many records have multiple semicolon-separated segments?
multi_segment = df["OPERATING_HOURS"].fillna("").str.count(";") > 1
print(f"Records with multiple hour segments: {multi_segment.sum()}")

# How many are always-open vs. scheduled?
always_open = df["OPERATING_HOURS"].fillna("").str.contains("00:00-23:59")
print(f"Always-open (or matching that pattern): {always_open.sum()} / {len(df)}")

# Location description & floor-level survey — drives Person B's ambiguity flagger
df["desc_len"] = df["AED_LOCATION_DESCRIPTION"].fillna("").str.len()
print(df["desc_len"].describe())

AMBIGUOUS_TERMS = ["near", "beside", "opposite", "level", "vicinity", "around", "behind"]
df["desc_lower"] = df["AED_LOCATION_DESCRIPTION"].fillna("").str.lower()
for term in AMBIGUOUS_TERMS:
    print(f"'{term}': {df['desc_lower'].str.contains(term).sum()} records")

print(df["AED_LOCATION_FLOOR_LEVEL"].value_counts().head(20))
print((df["AED_LOCATION_FLOOR_LEVEL"].fillna("").str.strip() == "").sum(), "missing floor level")

# Geographic distribution — drives district choice
df["postal_str"] = df["POSTAL_CODE"].astype(str).str.zfill(6)
df["postal_sector"] = df["postal_str"].str[:2]
sector_counts = df["postal_sector"].value_counts()
print(sector_counts.head(20))

# quick visual sanity check
import matplotlib.pyplot as plt
plt.scatter(df["lon"], df["lat"], s=2, alpha=0.3)
plt.title("AED spatial distribution — look for dense, non-resort clusters")
plt.savefig("scripts/aed_spatial_scatter.png")

# Interactive Map;
import folium

m = folium.Map(location=[1.3521, 103.8198], zoom_start=11)
for _, row in df.sample(min(500, len(df))).iterrows():
    folium.CircleMarker([row["lat"], row["lon"]], radius=2).add_to(m)
m.save("scripts/aed_overview_map.html")