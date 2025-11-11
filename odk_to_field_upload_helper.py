import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

# Use file dialog to select input CSV
import tkinter as tk
from tkinter import filedialog

# Hide the main tkinter window
tk.Tk().withdraw()

# Ask user to choose the CSV file
input_csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv")]
)

if not input_csv_path:
    raise FileNotFoundError("No CSV file selected.")

# Set pyogrio as default engine for geopandas
gpd.options.io_engine = "pyogrio"

# Read data
data = pd.read_csv(input_csv_path)

# Replace 'odk' in comments
data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)

# Create import DataFrame
import_df = pd.DataFrame({
    "relations.isRecordedIn": data["site_survey_area"],
    "identifier": data["identifier"],
    "scanCode": data["find_id"],
    "date": pd.to_datetime(data["today"]).dt.strftime("%d.%m.%Y"),
    "amount": data["find_quantity"],
    "spatialLocation": (
        "" + data["find_id"].astype(str) +
        "\nGround Visibility: " + data["ground_visibility"].astype(str) +
        "\nGeopoint Accuracy: " + data["geopoint-Accuracy"].astype(str)
    ),
    "category": data["find_type"]
})

# Map category values
category_mapping = {
    "ceramic / pottery": "Pottery",
    "stone finds": "Stone",
    "tiles / bricks": "Brick",
    "small finds": "Find",
    "other": "Find",
    "terracotta finds": "Terracotta",
    "water pipes": "Terracotta",
    "coins": "Coin",
    "metal objects": "Metal"
}
import_df["category"] = import_df["category"].replace(category_mapping)

# Find duplicates
duplicates = import_df["scanCode"].value_counts()
duplicates = duplicates[duplicates > 1]

# Create output folder
os.makedirs("out", exist_ok=True)

# Save categorized CSVs
for category in import_df["category"].dropna().unique():
    this_cat = import_df.loc[
        import_df["category"] == category, import_df.columns != "category"
    ].dropna(subset=["scanCode"])

    if not this_cat.empty:
        dupl_idx = this_cat["scanCode"].isin(duplicates.index)
        if dupl_idx.any():
            this_cat.loc[~dupl_idx].to_csv(f'out/import.{category}.csv', index=False)
            this_cat.loc[dupl_idx].to_csv(f'out/import.{category}_duplicates.csv', index=False)
        else:
            this_cat.to_csv(f'out/import.{category}.csv', index=False)

# --- Geodata ---
geodata = data.loc[data["identifier"] != "", ["geopoint-Longitude", "geopoint-Latitude", "identifier"]]
geodata = gpd.GeoDataFrame(
    geodata,
    geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
    crs="EPSG:4326"
)
geodata = geodata.to_crs(epsg=32635)
geodata.to_file("out/Field.Points.geojson", driver="GeoJSON")
