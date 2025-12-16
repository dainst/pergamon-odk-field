import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

root = tk.Tk()
root.withdraw()

# Set pyogrio as default engine for geopandas
gpd.options.io_engine = "pyogrio"

input_csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv")]
)
if not input_csv_path:
    raise FileNotFoundError("No CSV file selected.")

# Since we have users interacting with the script via a UI, 
# we want to communicate errors and problems to them in the same way. 
# We use a messagebox to inform them. 
try:
    data = pd.read_csv(input_csv_path)
except Exception as e:
    print(f"Error: Could not read CSV file - {e}")
    messagebox.showwarning("Warning", f"Could not process file:\n{e}")
    root.destroy()
    sys.exit(1)


#TODO at this point, check that all the required columns exist and warn if they do not
# workflow is restrictive, but this is an error that MIGHT occur if people manually edit the 
# files and we should at least inform them accordingly


# Reformat comment into a more informative description in iDAI.field
data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)

# Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
# identifier = unique name, relations.isRecordedIn = Trench/Operation, 
# scanCode = QR-Code, date = #TODO this has to be redone to conform to the new inputType!
# amount = number of finds/fragments, spatialLocation = description of the spatial 
# location (here: additional information about the geometry and find circumstances)
# category = the category of resource to import (will be used to split into multiple files)
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

#TODO I will want to add a warning window for categories that are not defined;
# since the workflow is restrictive, it probably does not happen, and yet it MIGHT

# Find duplicates
duplicates = import_df["scanCode"].value_counts()
duplicates = duplicates[duplicates > 1]
#TODO consider adding the number of duplicate entries to the success-messagebox, as this is important
# info that needs to be dealt with


# Create output folder
os.makedirs("out", exist_ok=True)
#TODO should we make sure its empty? what happens if it is not? 
# are we okay with overwriting? should we not ask?

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



messagebox.showinfo("Success", "CSV processed successfully")
root.destroy()
