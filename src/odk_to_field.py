import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Beginner friendly settings (edit these)
RECORDED_IN = "Survey Import" # FieldDesktop survey area to import into
OUTPUT_GEOJSON_NAME = "Field.Points.geojson"

root = tk.Tk()
root.withdraw()

# Define this as a shorthand to shutting down the script properly
def shutdown(success: bool = False):
    try:
        root.destroy()
    except Exception:
        pass

    if success:
        print("Closing with success.")
        sys.exit(0)
    else: 
        print("Closing with errors.")
        sys.exit(1)

# -- Geopandas enginge: Set pyogrio as default --
try:
    gpd.options.io_engine = "pyogrio"
except Exception:
    pass

# -- Select input CSV file --
input_csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv")]
)
if not input_csv_path:
    messagebox.showerror(title = "Error", message = "No CSV file selected.")
    shutdown()
#    raise FileNotFoundError("No CSV file selected.")

# -- Read CSV file --
# Since we have users interacting with the script via a UI, 
# we want to communicate errors and problems to them in the same way. 
# We use a messagebox to inform them. 
try:
    data = pd.read_csv(input_csv_path)
except Exception as e:
    print(f"Error: Could not read CSV file - {e}")
    messagebox.showerror(title = "Error", message = f"Could not process file:\n{e}")
    shutdown()

# -- Validate required columns --
# Every key that is required in this script needs to be listed here to compare
# the imported dict, and give a meaningful error message if one of the columns/keys
# is missing: 
required_keys = [
    "comment", 
    "find_id", 
    "today", 
    "find_quantity", 
    "ground_visibility", 
    "geopoint-Accuracy", 
    "find_type", 
    "geopoint-Longitude", 
    "geopoint-Latitude"
]
present_keys = set(data.columns) 

# To ensure that the script can progress safely, we check if all our required keys (columns) exist in the
# imported file and notify the user accordingly if they do not:
missing_keys = [k for k in required_keys if k not in present_keys]
if missing_keys:
    print(f"Error: Missing columns in CSV file: {', '.join(missing_keys)}")
    messagebox.showerror(
        title="Error", 
        message=f"Could not process file, missing columns:\n {', '.join(missing_keys)} ")
    shutdown()

# -- Remove rows without a valid find_id --
data["find_id"] = data["find_id"].fillna("").astype(str).str.strip()

rows_before = len(data)
data = data[data["find_id"] != ""].copy()
rows_removed = rows_before - len(data)

if rows_removed > 0:
    messagebox.showinfo(
        "Info",
        f"{rows_removed} row(s) without a find_id were ignored."
    )

# -- Comment formatting --
# Reformat comment into a more informative description in iDAI.field
data["comment"] = data["comment"].fillna("").astype(str)
data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)

# -- Category mapping --
# We have a pre-defined set of values for find_type which needs to be translated into iDAI.field 
# terminology, conforming to the pergamongrabung-1 project configuration. 
# Therefore, we define the mapping here:
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
# And then proceed to check the imported csv file for non-conforming values. 
data["find_type"] = data["find_type"].fillna("").astype(str)
present_categories = set(data["find_type"])

undefined_categories = sorted(present_categories - set(category_mapping.keys()) - {""})
if undefined_categories:
    print(
        "Warning: The following values in 'find_type' are unsupported: "
        + ", ".join(undefined_categories)
    )
    proceed = messagebox.askokcancel(
        title="Warning",
        message=(
            "The following values in 'find_type' are unsupported:\n"
            f"{', '.join(undefined_categories)}\n\n"
            "Proceed and set them to 'Find' category?"
        ),
    )
    if proceed:
        # The user is asked if they want to proceed by just importing those as "Find", which should usually be the
        # best solution in that case; but they can also abort to manually fix the csv-File. We add the previously
        # unsupported categories to the mapping dict and define them as "Find"s.
        category_mapping.update(dict.fromkeys(undefined_categories, "Find"))
    else: 
        shutdown()
# Last, we add category as a key that contains the reformated find_type to our data dict:
data["category"] = data["find_type"].replace(category_mapping)

# -- Duplicate find_id warning (show count) --
# Find duplicate find_id and warn if duplicates exist.
find_id_counts = data["find_id"].astype(str).value_counts()
dupl_find_ids = find_id_counts[find_id_counts > 1]
if len(dupl_find_ids) > 0:
    messagebox.showwarning(
        title="Duplicate 'find_id's",
        message=(
            f"The CSV contains {len(dupl_find_ids)} duplicate find_id value(s).\n"
            "Duplicates will be written into separate *_duplicates.csv files."
        ),
    )

# -- Build import DataFrame for iDAI.field --
# Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
# identifier = unique name, relations.isRecordedIn = Trench/Operation, 
# scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
# amount = number of finds/fragments, spatialLocation = description of the spatial 
# location (here: additional information about the geometry and find circumstances)
# category = the category of resource to import (will be used to split into multiple files)
import_df = pd.DataFrame({
    "relations.isRecordedIn": RECORDED_IN,
    "identifier": data["find_id"].astype(str),
    "scanCode": data["find_id"].astype(str),
    "date.value": pd.to_datetime(data["today"]).dt.strftime("%d.%m.%Y"),
    "date.endValue": "",
    "date.isRange": "false",
    "amount": data["find_quantity"],
    "spatialLocation": (
            data["find_id"].astype(str)
            + "\nGround Visibility: "
            + data["ground_visibility"].astype(str)
            + "\nGeopoint Accuracy: "
            + data["geopoint-Accuracy"].astype(str)),
    "category": data["category"],})

# -- Duplicates for output splitting --
scan_counts = import_df["scanCode"].value_counts()
duplicates = scan_counts[scan_counts > 1]

# -- Select output directory --
output_dir = filedialog.askdirectory(title="Select output directory")
if not output_dir:
    messagebox.showerror(title="Error", message="No output directory selected.")
    shutdown()

output_dir_files = os.listdir(output_dir)
if len(output_dir_files) != 0:
    proceed = messagebox.askokcancel(
        title="Directory not empty",
        message=(
            "The selected output directory is not empty.\n"
            "Files may be overwritten.\n\nDo you wish to proceed?"
        ),
    )
    if not proceed:
        shutdown()


# -- Save categorized CSV files --
written_files = 0
written_dupl_files = 0

for category in import_df["category"].dropna().unique():
    this_cat = import_df.loc[
        import_df["category"] == category, import_df.columns != "category"
    ].dropna(subset=["scanCode"])

    if this_cat.empty:
        continue

    dupl_idx = this_cat["scanCode"].isin(duplicates.index)
    if dupl_idx.any():
        out1 = os.path.join(output_dir, f"import.{category}.csv")
        out2 = os.path.join(output_dir, f"import.{category}_duplicates.csv")
        this_cat.loc[~dupl_idx].to_csv(out1, index=False)
        this_cat.loc[dupl_idx].to_csv(out2, index=False)
        written_files += 1
        written_dupl_files += 1
    else:
        out = os.path.join(output_dir, f"import.{category}.csv")
        this_cat.to_csv(out, index=False)
        written_files += 1

# -- Geodata (geojson) --
geodata = data.loc[data["find_id"].astype(str) != "", ["geopoint-Longitude", "geopoint-Latitude", "find_id"]].copy()
geodata = geodata.rename(columns={"find_id": "identifier"})

# Coerce lon/lat to numeric and drop invalid rows
geodata["geopoint-Longitude"] = pd.to_numeric(geodata["geopoint-Longitude"], errors="coerce")
geodata["geopoint-Latitude"] = pd.to_numeric(geodata["geopoint-Latitude"], errors="coerce")
geodata = geodata.dropna(subset=["geopoint-Longitude", "geopoint-Latitude"])

if not geodata.empty:
    gdf = gpd.GeoDataFrame(
        geodata,
        geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
        crs="EPSG:4326",
    )
    gdf = gdf.to_crs(epsg=32635)
    geojson_path = os.path.join(output_dir, OUTPUT_GEOJSON_NAME)
    gdf.to_file(geojson_path, driver="GeoJSON")

messagebox.showinfo(
    "Success",
    f"CSV processed successfully.\n\nCreated {written_files} import CSV file(s)"
    + (f" and {written_dupl_files} duplicate file(s)." if written_dupl_files else "."),
)
shutdown(success=True)
