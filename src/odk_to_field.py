# ------------------------
# Welcome! You can change and reuse this script for your own purposes. 
# We tried to keep it as simple as possible to help you adjust things
# just the way you want, even if you are a beginner at Python!
# This first part is not important for you, it handles the imported packages and the 
# "UI" = the window that opens for a user to interact with. 
# You can scroll down to the next heading to see where you might want or need 
# to change things. 
# 
# Have fun & kolay gelsin!
#
# ----------Imports and UI-------------------------------------------------------------------------
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

# This will open a file selection right at the start of the script, so you can choose which csv-file
# you want to process. 
input_csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv")]
)
if not input_csv_path:
    messagebox.showerror(title = "Error", message = f"No file selected.")
    shutdown()

# Since we have users interacting with the script via a UI, 
# we want to communicate errors and problems to them in the same way. 
# We use a messagebox to inform them. 
try:
    data = pd.read_csv(input_csv_path)
except Exception as e:
    print(f"Error: Could not read CSV file - {e}")
    messagebox.showerror(title = "Error", message = f"Could not process file:\n{e}")
    shutdown()


# ----------CSV-File Columns-------------------------------------------------------------------------
# For this script to work, we need the csv-file that you use it on to have 
# specific columns. These are then used as "keys" by this script. 
# Every "key" (= column) that is required in this script needs to be listed here 
# check whether the script can actually process your data or not: 
required_keys = [
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

# Now this part won't require any changes on your side again. 
# To ensure that the script can progress safely, we check if all our required keys (columns) exist in the
# imported file and notify the user accordingly if they do not:
if not set(required_keys).issubset(set(present_keys)):
    missing_keys = set(required_keys) - set(present_keys)
    print(f"Error: Missing columns in CSV-File: {', '.join(missing_keys)}")
    messagebox.showerror("Error", f"Could not process file, missing columns:\n {', '.join(missing_keys)} ")
    shutdown()

# ----------Defining 'categories' for iDAI.field------------------------------------------------------------------------
# We have a pre-defined set of values for find_type which needs to be translated into iDAI.field 
# terminology, conforming to the pergamongrabung-1 project configuration. 
# Therefore, we define the mapping here:
category_mapping = {
    # "value in the csv": "CategoryInField",
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
# You can change this mapping by removing or adding pairs. If you, e.g., also want to add Sculpture as an option
# and have it defined as a category in iDAI.field, you can add another pair like "sculpture":"Sculpture"

# And here we proceed to check the imported csv-File for non-conforming values. You won't need to change this. 
data["category"] = data["find_type"].replace(category_mapping)
# Be aware that there is no error-handling here for the sake of simplicity. 
# If your "find_type" column in the csv-file contains any value that is not listed in 
# the mapping above, the script should fail!



# ----------Set up how the csv you're importing in iDAI.field will look-------------------------------------------------
# Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
# identifier = unique name, relations.isRecordedIn = Trench/Survey Area/etc. (any Operation), 
# scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
# amount = number of finds/fragments, spatialLocation = description of the spatial 
# location (here: additional information about the geometry and find circumstances)
# category = the category of resource to import (will be used to split into multiple files)
# (A DataFrame is a special kind of structure from the pandas (pd) library. It makes it easier to 
# handle data that comes in the form of a "table" (like a csv-file") with python.)
import_df = pd.DataFrame({
    # Change the target parent resource here by replacing "Survey Import" with the name of the 
    # Operation you want to import your data to!
    "relations.isRecordedIn": "Survey Import",
    "shortDescription": "Imported from ODK",
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
# You can adjust all of the above to your needs. Simply write the name of the field from iDAI.filedialog
# you want to fill on the left (e.g. "shortDescription") in the same way you see it in the csv-exports from
# iDAI.field, and the column from you csv-file that you are transforming on the right, 
# for example: "data["your_column_name"]"



# ----------Select an output directory----------------------------------------------------------------------------------
# Here, we are opening another file dialog that will prompt you to select the directory you want to save your files
# in. You won't need to change this. 
output_dir = filedialog.askdirectory(title = "Select output directory")
output_dir_files = os.listdir(output_dir)
if len(output_dir_files) != 0:
    proceed = messagebox.askokcancel(title = "Directory not empty", message="The selected output directory is not empty. Files may be overwritten. Do you wish to proceed?")
    if not proceed:
        shutdown()
# The message box will appear to warn you if the directory you selected is not empty. It is because we don't want
# you to accidentally overwrite other files. ;)




# ----------Checking for duplicates------------------------------------------------------------------------
# Find duplicate find_id and warn if duplicates exist. Since we use the find_id as the QR-Code and 
# the identifier in iDAI.field, and iDAI.field needs the two to be unique, we are just checking if 
# your data has more than one entry for each find_id:
duplicates = data["find_id"].value_counts()
duplicates = duplicates[duplicates > 1]
if duplicates.count() > 0:
    duplicates.to_csv(f'{output_dir}/duplicates.txt', index=True)
    messagebox.showwarning(
        title = "Duplicate 'find_id's", 
        message = "The CSV-File contains duplicates - check 'duplicates.txt' in your output directory."
    )
# You can then write down the duplicate "find_id"s and delete or rename them in the output files.


# ----------Save a new CSV for each category----------------------------------------------------------------------------
# This is a loop! Here, we go through each unique value in the "category" column for our iDAI.field imports
# to make sure that we can write a new file for each of them, since this is how iDAI.field wants you to import data.
for category in import_df["category"].dropna().unique():
    # In each iteration, we select the rows from our csv / DataFrame that contain the current value for
    # category, and we immediately remove the "category" column from our new subset called "this_cat":
    this_cat = import_df.loc[
        import_df["category"] == category, import_df.columns != "category"
    ]
    
    # And then we simply save all our selected rows in "this_cat" (the category, not the animal) to a new csv-file
    # in the output directory you selected earlied. The files are named to that iDAI.field immediately understands
    # which category you want this impoort to be. You can change the file name though:
    this_cat.to_csv(f'{output_dir}/import.{category}.csv', index=False)

# ----------Processing the Geodata--------------------------------------------------------------------------------------
# To transform and then save the geodata, we first select everything that we want to appear in out "GeoJSON" file in 
# the end, meaning the x and y coordinates as well as the find_id.
geodata = data.loc[data["find_id"] != "", ["geopoint-Longitude", "geopoint-Latitude", "find_id"]]
# We have to rename the "find_id" to identifier again, because that is what iDAI.field needs as a property for each 
# feature in the resulting GeoJSON file. 
geodata = geodata.rename({"find_id": "identifier"})
# And then we set the Coordinate Reference System for our original data. Since ODK saved it as EPSG:4326, this is 
# what we use here. 
geodata = gpd.GeoDataFrame(
    geodata,
    geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
    # Change this to another EPSG-Code if your data uses another CRS!
    crs="EPSG:4326"
)
# And here, we need to transform our data to another CRS, which in this case is EPSG:32635 for the UTM-Zone
# Pergamon is located in, as that is the CRS the excavation uses in their database. 
# You can change this to your own target CRS by changing the number after "epsg=" in .to_crs():
geodata = geodata.to_crs(epsg=32635)

# And last but not least, we save the GeoJSON! All categories go in the same file here. Of course, 
# you can change the file name here:
geodata.to_file(f"{output_dir}/Field.Points.geojson", driver="GeoJSON")

# Just a friendly notification that the whole process has finished now, and we can close the script: 
messagebox.showinfo("Success", "CSV processed successfully")
shutdown(success = True)
