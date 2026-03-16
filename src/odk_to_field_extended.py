# File System Operations
import os
import sys

# UI
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkcalendar import DateEntry

# Geo
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


class ODKToField:
    # If we ever want this to be truly configurable and expandable, we may outsource the 
    # config here to files that can be read by a resulting exe, so that users would not need
    # to build it from the code. However, this is clearly not the current use case and I think 
    # we best leave it as it is right now. 
    # -- Config / defaults --
    # RECORDED_IN sets the Operation in Field Desktop data should be imported to. This is expected to be
    # any of the Operation-subcategories which allow adding Find-resources to them directly. 
    # The resource (in this case "ODK Import Data") has to exist, otherwise imports will fail. 
    RECORDED_IN_DEFAULT = "ODK Import Data"
    TARGET_CRS_EPSG = 32635 # UTM zone 35N; adjust if needed

    CATEGORY_MAPPING_DEFAULT = {
        "ceramic / pottery": "Pottery",
        "stone finds": "Stone",
        "tiles / bricks": "Brick",
        "small finds": "Find",
        "other": "Find",
        "terracotta finds": "Terracotta",
        "water pipes": "Terracotta",
        "coins": "Coin",
        "metal objects": "Metal",
    }

    REQUIRED_KEYS = [
        "find_id",
        "today",
        "find_quantity",
        "ground_visibility",
        "geopoint-Accuracy",
        "find_type",
        "geopoint-Longitude",
        "geopoint-Latitude",
    ]
        
    def __init__(self, root): 
        self.root = root
        self.root.title("ODK → Field Desktop Helper")
        self.root.minsize(800, 300)

        # -- Log window --
        # There is some console output that can be very informative for users. We want to log this, 
        # and display it to the users, so that they have some understanding of what goes right or wrong: 
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Consolas", 10)
        )
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # -- Buttons --
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        # -- Date picker --
        # We add a simple date picker, so that we may select the imported file by a specific day and are
        # able to create specific import files for each day of work - this is important, because we do not
        # want to duplicate imports to iDAI.field after their identifiers have been changed there and make sure 
        # that each object is only imported once. The date picker will default to 'today'. 

        # --- Step 1: Workflow hint label ---
        tk.Label(
            button_frame,
            text="Step 1: Choose date →",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        # -- Date picker --
        self.date_picker = DateEntry(button_frame, selectmode='day')
        self.date_picker.pack(side=tk.LEFT, padx=5, expand=True)

        # -- Process button SECOND --
        # Even though the user will only want to process one file, one time, we still let them manually 
        # (re)start the process, since it can be aborted by some errors. This way, the users does not
        # have to restart the application itself to try another file or re-try the same file after fixing
        # problems. 
        # --- Step 2: Workflow hint label ---
        tk.Label(
            button_frame,
            text="Step 2: Choose File and Start Processing →",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        # -- Pick file and start processing --
        self.start_button = tk.Button(
            button_frame,
            text="Start",
            command=self.run,
            font=("Arial", 12)
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        # -- Quit button --
        self.quit_button = tk.Button(
            button_frame,
            text="Quit",
            command=self.shutdown,
            font=("Arial", 12)
        )
        self.quit_button.pack(side=tk.LEFT, padx=5)

        # -- Geopandas engine --
        # Set pyogrio as default engine for geopandas
        try:
            gpd.options.io_engine = "pyogrio"
        except Exception:
            # Keep working even if pyogrio is missing
            pass

        self.log("Ready to process CSV files...")
        self.log("")
        self.log("Workflow (day-by-day export):")
        self.log("  1) Choose the date you want to filter for")
        self.log("  2) Click 'Start'")
        self.log("  3) Select the ODK CSV file")
        self.log("  4) Select an output directory")
        self.log("  5) Import the generated files into Field Desktop")
        self.log("")
        self.log("Tip: The date filter ensures each survey day is exported separately.")

    def log(self, message: str):
        """Logs messages to the root window."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def select_input_file(self) -> str | None:
        """Opens the file dialog that prompts users to select the input csv-file, return the path or None if canceled."""
        return filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv")]
        )

    def select_output_directory(self) -> str | None:
        """Select output dir; if not empty, ask whether to proceed."""
        while True:
            output_dir = filedialog.askdirectory(title = "Select output directory")
            if not output_dir:
                messagebox.showinfo("Cancelled", "No directory selected")
                return None
            
            try:
                output_dir_files = os.listdir(output_dir)
            except Exception as e:
                self.log(f"Error: Could not access output directory - {e}")
                messagebox.showerror("Error", "Could not access the selected directory.")
                return None

            if len(output_dir_files) == 0:
                return output_dir

            proceed = messagebox.askokcancel(
                title="Directory not empty",
                message=(
                    "The selected output directory is not empty.\n"
                    "Files may be overwritten.\n\nDo you wish to proceed?"
                ),
            )
            if proceed:
                return output_dir
            # else: loop again and let them choose a different folder

# -- -- -- -- -- -- -- -- -- -- -- -- 
# -- Validation / transformation --
# -- -- -- -- -- -- -- -- -- -- -- --
    def all_columns_present_in_input(self, data: pd.DataFrame) -> bool:
        """Check if all required keys/columns are present in the input file."""
        present_keys = set(data.columns)
        missing = [k for k in self.REQUIRED_KEYS if k not in present_keys]
        if missing:
            self.log(f"Error: Missing columns in CSV file: {', '.join(missing)}")
            messagebox.showerror(
                "Error",
                f"Could not process file, missing columns:\n{', '.join(missing)}",
            )
            return False
        return True

    def filter_rows_without_find_id(self, data: pd.DataFrame) -> pd.DataFrame | None:
        """Remove rows without a real identifier (NaN, empty string, whitespace)."""
        data["find_id"] = data["find_id"].fillna("").astype(str).str.strip()

        before = len(data)
        data = data[data["find_id"] != ""].copy()
        removed = before - len(data)

        if removed > 0:
            self.log(f"Ignored {removed} row(s) without a valid find_id.")

        if len(data) == 0:
            messagebox.showerror("Error", "No rows with valid 'find_id' in data.")
            return None

        return data

    def filter_by_date(self, data: pd.DataFrame) -> pd.DataFrame | None:
        """Filter by date selected in date picker. Robust to timestamps/time parts."""
        selected = pd.to_datetime(self.date_picker.get_date()).date()

        data["today"] = pd.to_datetime(data["today"], errors="coerce")
        invalid_sum = int(data["today"].isna().sum())
        if invalid_sum > 0:
            invalid_ids = data["find_id"].loc[data["today"].isna()].fillna("NA").str.cat(sep = ", ")
            self.log(f"Warning: {invalid_sum} row(s) have invalid dates in column 'today' and will be ignored: {invalid_ids}.")
        # Consider: It may not be helpful to add the find_ids here, and we could instead use the rows. 
        # But: That makes the relevant data harder to find. Plus: I am sure this never happens with exports from 
        # ODK, since date it auto-generated. Therefore: No use in putting more effort into this topic.

        result = data[data["today"].dt.date == selected].copy()

        if len(result) == 0:
            messagebox.showinfo("No data", "No rows found for the selected date.")
            return None
        return result

    def map_categories(self, data: pd.DataFrame) -> pd.DataFrame | None:
        """Replaces the values in 'find_type' according to the category mapping defined in 
        `CATEGORY_MAPPING_DEFAULT`, with the names of the corresponding categories in iDAI.field."""
        mapping = dict(self.CATEGORY_MAPPING_DEFAULT)

        # If 'find_type' is not set, we set it so "missing". This way, it will be clearly communicated that
        # some rows have "missing" find_types - which is something we do not want either way, because everything
        # needs a category, and the user will be notified and prompted, and the category can be set as "Find" 
        # same as for other unsopported values. I put the "-" around "missing" to make it look a little more
        # technical - so it's clear this is generated. 
        data["find_type"] = data["find_type"].fillna("-missing-").astype(str).str.strip()

        present_categories = set(data["find_type"])
        undefined = sorted(present_categories - set(mapping.keys()))
        if undefined:
            self.log(
                "Warning: The following values in 'find_type' are unsupported: "
                + ", ".join(undefined)
            )
            proceed = messagebox.askokcancel(
                title="Warning",
                message=(
                    "The following values in 'find_type' are unsupported:\n"
                    f"{', '.join(undefined)}\n\n"
                    "Proceed and set them to 'Find' category?"
                ),
            )
            if proceed:
                mapping.update(dict.fromkeys(undefined, "Find"))
            else:
                return None

        data["category"] = data["find_type"].replace(mapping)
        return data

    def find_duplicates(self, data: pd.DataFrame) -> pd.Series:
        """Check for duplicate values of 'find_id', since iDAI.field needs unique identifiers. Returns the duplicates."""
        counts = data["find_id"].value_counts()
        duplicates = counts[counts > 1]
        if not duplicates.empty:
            self.log(f"Warning: {len(duplicates)} duplicate 'find_id' value(s) found:")
            self.log(duplicates.to_string())
        return duplicates

# -- -- -- -- -- -- -- -- --
# -- Build export formats --
# -- -- -- -- -- -- -- -- --
    def build_field_data(self, data: pd.DataFrame) -> pd.DataFrame | None:
        """Structure the data as required by iDAI.field. Formats the date, and sets the 
        appropriate names for the columns in the resulting data. This method will require a
        pre-formatted date as produced by filter_by_date()."""

        data = data.copy()
        data["field_date"] = data["today"].dt.strftime("%d.%m.%Y")

        # Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
        # identifier = unique name, relations.isRecordedIn = Trench/Operation, 
        # scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
        # amount = number of finds/fragments, spatialLocation = description of the spatial 
        # location (here: additional information about the geometry and find circumstances)
        # category = the category of resource to import (will be used to split into multiple files)
        field_data = pd.DataFrame({
            "relations.isRecordedIn": self.RECORDED_IN_DEFAULT,
            "shortDescription": "Imported from ODK",
            "identifier": data["find_id"].astype(str),
            "scanCode": data["find_id"].astype(str),
            "date.value": data["field_date"],
            "date.endValue": "",
            "date.isRange": "false",
            # We could coerce find_quantity to integer, but iDAI.field will warn accordingly on import. 
            # Since ODK-Exports are automated, the user would need to address this mismatch in the
            # resulting import file for iDAI.field either way. This, no type checking and coercion here.
            # We let Field handle it.  
            "amount": data["find_quantity"],
            "spatialLocation": (
                "Imported from ODK: " + data["find_id"].astype(str) +
                ", Ground Visibility: " + data["ground_visibility"].astype(str) +
                ", Geopoint Accuracy: " + data["geopoint-Accuracy"].astype(str)
            ),
            "category": data["category"]
        })
        
        return field_data

    def save_csv_output(self, field_data: pd.DataFrame, duplicates: pd.Series, output_dir: str):
        """Iterates over all categories in the data and writes a csv file for each category, a second one
        if this category contains any duplicate identifiers. Duplicates are not neccessarily of the same
        category."""
        # Since iDAI.field needs one file for each category it will import, we are saving a new csv-File 
        # for each category present in the data. If there are rows with duplicates, 
        # these are saved in a specific "duplicates" file for manual review and merging. 
        # The files are named so that iDAI.field will automatically recognize the category from the file name. 
        selected_date = pd.to_datetime(self.date_picker.get_date()).strftime("%Y_%m_%d")
        
        # stable category order
        categories = sorted([c for c in field_data["category"].dropna().unique()])

        for category in categories:
            this_cat = field_data.loc[
                field_data["category"] == category, field_data.columns != "category"
            ].dropna(subset=["identifier"])

            if this_cat.empty:
                continue

            filename = f"{selected_date}_import.{category}.csv"
            out_path = os.path.join(output_dir, filename)

            dupl_idx = this_cat["identifier"].isin(duplicates.index)

            # If you arrive here and notice that this will write 0 resources to the import csv if the only 
            # row for that category contains a duplicate: I know. 
            # It is not ideal, but also an edge case and I do not want to guard against it, because another check 
            # would bring complexity with no real benefit. I think it is fine to ignore this.
            # Let's call it a feature: I will prepare a new empty table for you to copy your cleaned up data into. ;) 
            if dupl_idx.any():
                filename_dupl = f"{selected_date}_duplicates.{category}.csv"
                out_path_dupl = os.path.join(output_dir, filename_dupl)

                self.log(f"Writing {len(this_cat.loc[~dupl_idx])} resources to '{filename}'")
                this_cat.loc[~dupl_idx].to_csv(out_path, index=False)

                self.log(f"Writing {len(this_cat.loc[dupl_idx])} resources to '{filename_dupl}'")
                this_cat.loc[dupl_idx].to_csv(out_path_dupl, index=False)
            else:
                self.log(f"Writing {len(this_cat)} resources to '{filename}'")
                this_cat.to_csv(out_path, index=False)

    def save_geodata(self, data: pd.DataFrame, duplicates: pd.Series, output_dir: str):
        """Transforms all geodata from EPSG:4326 to the selected CRS (see TARGET_CRS_EPSG). Writes all geodata to a 
        single GeoJSON Feature Collection file, using identifier (from 'find_id') as a property."""
        # Filter to valid identifiers + non-empty coordinates
        valid_rows = (
            data["find_id"].notna()
            & (data["find_id"].astype(str).str.strip() != "")
            & data["geopoint-Longitude"].notna()
            & data["geopoint-Latitude"].notna()
        )
        # We select the appropriate columns for the GeoJSON import, for which we only need the point coordinates and 
        # the find_id. We rename find_id to identifier as iDAI.field needs a property of that name for
        # import. 
        geodata = data.loc[valid_rows, ["geopoint-Longitude", "geopoint-Latitude", "find_id"]].copy()
        geodata = geodata.rename(columns={"find_id": "identifier"})

        # Coerce coordinates to numeric 
        geodata["geopoint-Longitude"] = pd.to_numeric(geodata["geopoint-Longitude"], errors="coerce")
        geodata["geopoint-Latitude"] = pd.to_numeric(geodata["geopoint-Latitude"], errors="coerce")
        geodata = geodata.dropna(subset=["geopoint-Longitude", "geopoint-Latitude"])

        if geodata.empty:
            self.log("No valid coordinate rows found — skipping GeoJSON export.")
            return
  
        gdf = gpd.GeoDataFrame(
            geodata,
            geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
            crs="EPSG:4326",
        ).to_crs(epsg=self.TARGET_CRS_EPSG)

        # -- Drop original coordinate columns --
        # We can remove the original geodata from the attributes; it makes the file larger and these attributes 
        # cannot be imported by iDAI.field anyway. 
        gdf = gdf.drop(columns=["geopoint-Longitude", "geopoint-Latitude"])

        selected_date = pd.to_datetime(self.date_picker.get_date()).strftime("%Y_%m_%d")
        filename = f"{selected_date}_import.Points.geojson"
        out_path = os.path.join(output_dir, filename)

        dupl_idx = gdf["identifier"].isin(duplicates.index)
        if dupl_idx.any():
            filename_dupl = f"{selected_date}_duplicates.Points.geojson"
            out_path_dupl = os.path.join(output_dir, filename_dupl)
            # All duplicates are written to a file, which should make it easier to sort them out manually in a text-editor. 
            self.log(f"Writing {len(gdf.loc[dupl_idx])} features to '{filename_dupl}'")
            gdf.loc[dupl_idx].to_file(out_path_dupl, driver="GeoJSON")
            # And the rows which do not contain duplicates are written to the "normal" import file. 
            self.log(f"Writing {len(gdf.loc[~dupl_idx])} features to '{filename}'")
            gdf.loc[~dupl_idx].to_file(out_path, driver="GeoJSON")
        else: 
            self.log(f"Writing {len(gdf)} features to '{filename}'")
            gdf.to_file(out_path, driver="GeoJSON")

# -- -- -- -- -- --
# -- Main action --
# -- -- -- -- -- -- 
    def run(self):
        # Please note: All methods in this class are currently meant to run in the order that they are
        # referenced here in the run() method. Now, this is not actually good practice. They should 
        # probably be private methods instead. However, we do not expect anyone to use it in such a 
        # way that this oversight would impact anyone.        
        self.start_button.config(state=tk.DISABLED)

        input_csv_path = self.select_input_file()
        if not input_csv_path:
            self.log("Cancelled: No file selected.")
            return
        
        self.log(f"Processing file: {input_csv_path}")
        
        # Since we have users interacting with the script via a UI, 
        # we want to communicate errors and problems to them in the same way. 
        # We use a messagebox to inform them - here and in all methods. 
        try:
            data = pd.read_csv(input_csv_path)
        except Exception as e:
            self.log(f"Error: Could not read CSV file - {e}")
            messagebox.showerror(title = "Error", message = f"Could not read CSV file:\n{e}")
            return

        # We need to check if all the columns needed for further processing are present
        # and will abort the run gracefully if they are not, so that the user can fix the 
        # csv-file and try again.  
        if not self.all_columns_present_in_input(data):
            self.log("Processing cancelled.")
            return
        
        # Here, we select the content of the csv file by the date selected in the date picker. 
        # This allows imports of only a single day. We should filter by date first, because otherwise all the following 
        # messages would be confusing to users.
        self.log(f"Filtering for date: {self.date_picker.get_date()}")
        data = self.filter_by_date(data)
        if data is None: 
            self.log("Processing cancelled.")
            return

        # Filter empty/whitespace find_id rows, because we only want to import the finds that have a scanCode and thus
        # a find_id in iDAI.field. Normal survey points referencing finds that have been left in the field have no 
        # place in the database. We do this after filtering by date, so users can see how many record for this day have 
        # been skipped. 
        data = self.filter_rows_without_find_id(data)
        if data is None:
            self.log("Processing cancelled.")
            return
        
        # -- Map categories --
        # We reassign here as the original data is being changed, with a new category-key being added. 
        # If mapping the find_type to the pre-defined categories goes wrong, we exit gracefully so that
        # the user can fix the file manually and try again. 
        data = self.map_categories(data)
        if data is None: 
            self.log("Processing cancelled.")
            return

        # -- Duplicates --
        # Am unsure if this is needed - Field Desktop itself does warn when trying to input multiple
        # 'find_id's, but I still see value in notifying people here. 
        duplicates = self.find_duplicates(data)
        
        # -- Build Field Desktop import data --
        # Last step in the transformation, we build the new dataframe in the format iDAI.field expects:
        field_data = self.build_field_data(data)
        if field_data is None:
            self.log("Processing cancelled.")
            return
        # TODO needs error handling and clear communication about malformed input file.

        output_dir = self.select_output_directory()
        if not output_dir:
            self.log("Cancelled. No output directory selected")
            return

        self.log(f"Writing CSV and GeoJSON output files to directory: {output_dir}")
        
        try: 
            self.save_csv_output(field_data, duplicates, output_dir)
        except Exception as e:
            self.log(f"Error: Could not save CSV files - {e}")
            messagebox.showerror(title = "Error", message = f"Could not save CSV files.")
            return

        try: 
            self.save_geodata(data, duplicates, output_dir)
        except Exception as e:
            self.log(f"Error: Could not save geodata - {e}")
            messagebox.showerror(title = "Error", message = f"Could not save geodata.")
            return

        self.log(f"Processing file '{os.path.basename(input_csv_path)}' finished.")
        messagebox.showinfo("Success", "CSV processed successfully.")
        self.start_button.config(state=tk.NORMAL)

        return

    def shutdown(self):
        self.root.quit()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ODKToField(root)
    root.mainloop() 


if __name__ == "__main__":
    main()
