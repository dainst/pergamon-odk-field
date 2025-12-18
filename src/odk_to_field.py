import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


class ODKToField:
    def __init__(self, root): 
        self.root = root
        
        # There is some console output that can be very informative for users. We want to log this, 
        # and display it to the users, so that they have some understanding of what goes right or wrong. 
        self.root.minsize(800, 300)
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Consolas", 10)
        )
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        # Even though the user will only want to process one file, one time, we still let them manually 
        # (re)start the process, since it can be aborted by some errors. This way, the users does not
        # have to restart the application itself to try another file or re-try the same file after fixing
        # problems. 
        self.start_button = tk.Button(
            button_frame,
            text="Process CSV",
            command=self.run,
            font=("Arial", 12)
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.quit_button = tk.Button(
            button_frame,
            text="Quit",
            command=self.shutdown,
            font=("Arial", 12)
        )
        self.quit_button.pack(side=tk.RIGHT, padx=5)


        # Set pyogrio as default engine for geopandas
        gpd.options.io_engine = "pyogrio"

        self.log("Ready to process CSV files...")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def select_input_file(self):
        input_csv_path = filedialog.askopenfilename(
            title="Select the CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        return input_csv_path

    def select_output_directory(self):
        output_dir = filedialog.askdirectory(title = "Select output directory")
        if not output_dir:
            messagebox.showinfo("Cancelled", "No directory selected")
            return None
        output_dir_files = os.listdir(output_dir)
        if len(output_dir_files) != 0:
            proceed = messagebox.askokcancel(
                title = "Directory not empty", 
                message="The selected output directory is not empty. Files may be overwritten. Do you wish to proceed?"
            )
            if not proceed:
                # We assume that not wanting to proceed with that directory will mean that the user wants to 
                # another directory that may not contain any files. If the users cancels the file selection, the whole
                # processing is cancelled. 
                return self.select_output_directory()
        
        return output_dir

    def all_columns_present_in_input(self, data):
        # Every key that is required in this script needs to be listed here to compare
        # the imported dict, and give a meaningful error message if one of the columns/keys
        # is missing: 
        required_keys = [
            "comment", 
            "site_survey_area", 
            "identifier", 
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
            self.log(f"Error: Missing columns in CSV-File: {', '.join(missing_keys)}")
            messagebox.showerror("Error", f"Could not process file, missing columns:\n{', '.join(missing_keys)} ")
            return False
        else: 
            return True

    def map_categories(self, data):
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
        present_categories = set(data["find_type"])
        if not present_categories.issubset(set(category_mapping.keys())):
            undefined_categories = present_categories - set(category_mapping.keys())
            self.log(f"Warning: The following values in 'find_type' are unsupported: {', '.join(undefined_categories)}")
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
                return None
        # Last, we add category as a key that contains the reformated find_type to our data dict:
        data["category"] = data["find_type"].replace(category_mapping)

        return(data)

    def log_duplicate_identifier(self, data):
        # Find duplicate identifiers and warn if duplicates exist.
        duplicates = data["identifier"].value_counts()
        duplicates = duplicates[duplicates > 1]
        if not duplicates.empty:
            self.log(f"Warning: Found {len(duplicates)} duplicate identifiers:")
            self.log(duplicates.to_string())
            messagebox.showwarning(
                title = "Duplicate identifiers", 
                message = f"The CSV-File contains duplicate {len(duplicates)} identifiers - check the output."
            )


    def build_field_data(self, data):
        # Reformat comment into a more informative description in iDAI.field
        data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)

        # Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
        # identifier = unique name, relations.isRecordedIn = Trench/Operation, 
        # scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
        # amount = number of finds/fragments, spatialLocation = description of the spatial 
        # location (here: additional information about the geometry and find circumstances)
        # category = the category of resource to import (will be used to split into multiple files)
        field_data = pd.DataFrame({
            "relations.isRecordedIn": data["site_survey_area"],
            "identifier": data["identifier"],
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
        # TODO A lot of things can still go wrong here, and we have no error handling for that at all. 
        # We currently assume the file will always be formated perfectly. 
        
        return(field_data)

    def save_csv_output(self, field_data, output_dir):
        # Find duplicates
        duplicates = field_data["scanCode"].value_counts()
        duplicates = duplicates[duplicates > 1]
        # TODO consider adding the number of duplicate entries to the success-messagebox, as this is important
        # info that needs to be dealt with
        # Also: I am confused here; do we really want to select the duplicate QR-Codes or the identifiers...?

        # Since iDAI.field needs one file for each category it will import, we are saving a new csv-File 
        # for each category present in the data. If there are rows with duplicates, 
        # these are saved in a specific "_duplicates" file for manual review and merging. 
        # The files are named so that iDAI.field will automatically recognize the category from the file name. 
        self.log(f"Writing output files to directory: {output_dir}")
        for category in field_data["category"].dropna().unique():
            this_cat = field_data.loc[
                field_data["category"] == category, field_data.columns != "category"
            ].dropna(subset=["scanCode"])

            if not this_cat.empty:
                dupl_idx = this_cat["scanCode"].isin(duplicates.index)
                if dupl_idx.any():
                    self.log(f"Writing {len(this_cat.loc[~dupl_idx])} resources to file 'import.{category}.csv'")
                    this_cat.loc[~dupl_idx].to_csv(f'{output_dir}/import.{category}.csv', index=False)
                    self.log(f"Writing {len(this_cat.loc[dupl_idx])} resources to file 'import.{category}_duplicates.csv'")
                    this_cat.loc[dupl_idx].to_csv(f'{output_dir}/import.{category}_duplicates.csv', index=False)
                else:
                    self.log(f"Writing {len(this_cat)} resources to file 'import.{category}.csv'")
                    this_cat.to_csv(f'{output_dir}/import.{category}.csv', index=False)


    def save_geodata(self, data, output_dir):
        geodata = data.loc[data["identifier"] != "", ["geopoint-Longitude", "geopoint-Latitude", "identifier"]]
        geodata = gpd.GeoDataFrame(
            geodata,
            geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
            crs="EPSG:4326"
        )
        geodata = geodata.to_crs(epsg=32635)
        self.log(f"Writing output files to directory: {output_dir}")
        self.log(f"Writing {len(geodata)} resources to file 'Field.Points.geojson'")
        geodata.to_file(f"{output_dir}/Field.Points.geojson", driver="GeoJSON")


    def run(self):
        input_csv_path = self.select_input_file()
        if not input_csv_path:
            self.log(f"Cancelled: No file selected")
            return 
        self.log(f"Processing file: {input_csv_path}")
        
        # Since we have users interacting with the script via a UI, 
        # we want to communicate errors and problems to them in the same way. 
        # We use a messagebox to inform them - here and in all methods. 
        try:
            data = pd.read_csv(input_csv_path)
        except Exception as e:
            self.log(f"Error: Could not read CSV file - {e}")
            messagebox.showerror(title = "Error", message = f"Could not process file:\n{e}")
            return

        # We need to check if all the columns needed for further processing are present
        # and will abort the run gracefully if they are not, so that the user can fix the 
        # csv-file and try again.  
        if not self.all_columns_present_in_input(data):
            self.log(f"Processing cancelled")
            return
        
        # We reassign here as the original data is being changed, with a new category-key being added. 
        # If mapping the find_type to the pre-defined categories goes wrong, we exit gracefully so that
        # the user can fix the file manually and try again. 
        data = self.map_categories(data)
        if data is None: 
            self.log(f"Processing cancelled")
            return

        # Am unsure if this is needed - Field Desktop itself does warn when trying to input multiple
        # identifiers, but I still see value in notifying people here. 
        self.log_duplicate_identifier(data)

        # Last step in the transformation, we build the new dataframe in the format iDAI.field expects:
        field_data = self.build_field_data(data)
        # TODO needs error handling and clear communication about malformed input file.

        output_dir = self.select_output_directory()
        try: 
            self.save_csv_output(field_data, output_dir)
        except Exception as e:
            self.log(f"Error: Could not save CSV files - {e}")
            messagebox.showerror(title = "Error", message = f"Could not save CSV files.")
            return

        try: 
            self.save_geodata(data, output_dir)
        except Exception as e:
            self.log(f"Error: Could not save geodata - {e}")
            messagebox.showerror(title = "Error", message = f"Could not save geodata.")
            return

        self.log(f"Processing file '{os.path.basename(input_csv_path)}' finished.")
        messagebox.showinfo("Success", "CSV processed successfully")
        return

    def shutdown(self):
        self.root.quit()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ODKToField(root)
    root.mainloop()  # Keep tkinter running


if __name__ == "__main__":
    main()
