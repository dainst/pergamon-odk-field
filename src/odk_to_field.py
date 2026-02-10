import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

root = tk.Tk()
root.withdraw()

# Define this as a shorthand to shutting down the script properly;
def shutdown(success = False):
    root.destroy()
    if success:
        print("Closing with success.")
        sys.exit(0)
    else: 
        print("Closing with errors.")
        sys.exit(1)

# Set pyogrio as default engine for geopandas
gpd.options.io_engine = "pyogrio"

input_csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv")]
)
if not input_csv_path:
    messagebox.showerror(title = "Error", message = f"Could not process file:\n{e}")
    shutdown()
#    raise FileNotFoundError("No CSV file selected.")

# Since we have users interacting with the script via a UI, 
# we want to communicate errors and problems to them in the same way. 
# We use a messagebox to inform them. 
try:
    data = pd.read_csv(input_csv_path)
except Exception as e:
    print(f"Error: Could not read CSV file - {e}")
    messagebox.showerror(title = "Error", message = f"Could not process file:\n{e}")
    shutdown()

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
present_keys = data.keys()

# To ensure that the script can progress safely, we check if all our required keys (columns) exist in the
# imported file and notify the user accordingly if they do not:
if not set(required_keys).issubset(set(present_keys)):
    missing_keys = set(required_keys) - set(present_keys)
    print(f"Error: Missing columns in CSV-File: {', '.join(missing_keys)}")
    messagebox.showerror("Error", f"Could not process file, missing columns:\n {', '.join(missing_keys)} ")
    shutdown()

# Reformat comment into a more informative description in iDAI.field
data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)

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
# And then proceed to check the imported csv-File for non-conforming values. 
# 
present_categories = set(data["find_type"])
if not present_categories.issubset(set(category_mapping.keys())):
    undefined_categories = present_categories - set(category_mapping.keys())
    print(f"Warning: The following values in 'find_type' are unsupported: {', '.join(undefined_categories)}")
    proceed = messagebox.askokcancel(
        title = "Warning", 
        message = f"The following values in 'find_type' are unsupported:\n {', '.join(undefined_categories)}\n\nProceed and set to 'Find' category?"
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


# Find duplicate find_id and warn if duplicates exist.
duplicates = data["find_id"].value_counts()
duplicates = duplicates[duplicates > 1]
if duplicates.count() > 0:
    print(duplicates)
    messagebox.showwarning(
        title = "Duplicate 'find_id's", 
        message = "The CSV-File contains duplicate 'find_id's (identifiers) - check the output."
    )

# Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
# identifier = unique name, relations.isRecordedIn = Trench/Operation, 
# scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
# amount = number of finds/fragments, spatialLocation = description of the spatial 
# location (here: additional information about the geometry and find circumstances)
# category = the category of resource to import (will be used to split into multiple files)
import_df = pd.DataFrame({
    # Change the target parent resource here by replacing "Survey Import" with the name of the 
    # Operation you want to import your data to!
    "relations.isRecordedIn": "Survey Import",
    "identifier": data["find_id"],
    "scanCode": data["find_id"],
    "date.value": pd.to_datetime(data["today"]).dt.strftime("%d.%m.%Y"),
    "date.endValue": "",
    "date.isRange": "false",
    "amount": data["find_quantity"],
    "spatialLocation": (
        "" + data["find_id"].astype(str) +
        "\nGround Visibility: " + data["ground_visibility"].astype(str) +
        "\nGeopoint Accuracy: " + data["geopoint-Accuracy"].astype(str)
    ),
    "category": data["category"]
})


# Find duplicates
duplicates = import_df["scanCode"].value_counts()
duplicates = duplicates[duplicates > 1]
#TODO consider adding the number of duplicate entries to the success-messagebox, as this is important
# info that needs to be dealt with


output_dir = filedialog.askdirectory(title = "Select output directory")
output_dir_files = os.listdir(output_dir)
if len(output_dir_files) != 0:
    proceed = messagebox.askokcancel(title = "Directory not empty", message="The selected output directory is not empty. Files may be overwritten. Do you wish to proceed?")
    if not proceed:
        shutdown()


# Save categorized CSVs
for category in import_df["category"].dropna().unique():
    this_cat = import_df.loc[
        import_df["category"] == category, import_df.columns != "category"
    ].dropna(subset=["scanCode"])

    if not this_cat.empty:
        dupl_idx = this_cat["scanCode"].isin(duplicates.index)
        if dupl_idx.any():
            this_cat.loc[~dupl_idx].to_csv(f'{output_dir}/import.{category}.csv', index=False)
            this_cat.loc[dupl_idx].to_csv(f'{output_dir}/import.{category}_duplicates.csv', index=False)
        else:
            this_cat.to_csv(f'{output_dir}/import.{category}.csv', index=False)

# --- Geodata ---
geodata = data.loc[data["find_id"] != "", ["geopoint-Longitude", "geopoint-Latitude", "find_id"]]
geodata = geodata.rename({"find_id": "identifier"})
geodata = gpd.GeoDataFrame(
    geodata,
    geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
    crs="EPSG:4326"
)
geodata = geodata.to_crs(epsg=32635)
geodata.to_file(f"{output_dir}/Field.Points.geojson", driver="GeoJSON")



messagebox.showinfo("Success", "CSV processed successfully")
shutdown(success = True)
