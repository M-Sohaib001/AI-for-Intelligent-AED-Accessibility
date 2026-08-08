import geopandas as gpd
import folium


AED_PATH = "data/scdf_aed_frozen.geojson"
BOUNDARY_PATH = "data/district_boundary.geojson"
OUTPUT = "scripts/final_boundary_inspection.html"


# Load AEDs
aeds = gpd.read_file(AED_PATH)

# Calculate postal sector
aeds["POSTAL_CODE"] = (
    aeds["POSTAL_CODE"]
    .astype(str)
    .str.zfill(6)
)

aeds["postal_sector"] = aeds["POSTAL_CODE"].str[:2]

sector_aeds = aeds[
    aeds["postal_sector"] == "73"
].copy()


# Load final boundary
boundary = gpd.read_file(BOUNDARY_PATH)


# Map center
centroid = boundary.to_crs("EPSG:3414").geometry.iloc[0].centroid
centroid_wgs84 = gpd.GeoSeries(
    [centroid],
    crs="EPSG:3414",
).to_crs("EPSG:4326").iloc[0]


m = folium.Map(
    location=[
        centroid_wgs84.y,
        centroid_wgs84.x,
    ],
    zoom_start=13,
)


# Boundary
folium.GeoJson(
    boundary.to_json(),
    name="Final Woodlands Boundary",
    style_function=lambda feature: {
        "fillOpacity": 0.15,
        "weight": 4,
    },
).add_to(m)


# AED points
for _, row in sector_aeds.iterrows():

    folium.CircleMarker(
        location=[
            row.geometry.y,
            row.geometry.x,
        ],
        radius=3,
        fill=True,
        popup=str(row["AED_ID"]),
    ).add_to(m)


folium.LayerControl().add_to(m)

m.save(OUTPUT)

print(f"Created: {OUTPUT}")