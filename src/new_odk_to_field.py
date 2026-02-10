import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkcalendar import DateEntry

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


        # We add a simple date picker, so that we may select the imported file by a specific day and are
        # able to create specific import files for each day of work - this is important, because we do not
        # want to duplicate imports to iDAI.field after their identifiers have been changed there and make sure 
        # that each object is only imported once. The date picker will default to 'today'. 
        self.date_picker = DateEntry(button_frame, selectmode='day')
        self.date_picker.pack(side=tk.LEFT, padx=5, expand=True)


        self.quit_button = tk.Button(
            button_frame,
            text="Quit",
            command=self.shutdown,
            font=("Arial", 12)
        )
        self.quit_button.pack(side=tk.LEFT, padx=5)


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

    def filter_by_date(self, data):
        # We are converting both time specifications into the same format (as used by pandas)
        # as we use the ps variant later in this script anyway. 
        selected_date = pd.to_datetime(self.date_picker.get_date())
        data["today"] = pd.to_datetime(data["today"])

        result = data[data["today"] == selected_date]
        if (len(result) == 0):
            return None
        else: 
            return result

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

    def find_duplicates(self, data):
        # Find duplicate `find_id`s and warn if duplicates exist, as they will be used as the identifier 
        # in iDAI.field, which has to be unique. 
        duplicates = data["find_id"].value_counts()
        duplicates = duplicates[duplicates > 1]
        if not duplicates.empty:
            self.log(f"Warning:  {len(duplicates)} duplicate 'find_id's:")
            self.log(duplicates.to_string())
        return duplicates


    def build_field_data(self, data):
        # Reformat comment into a more informative description in iDAI.field
        data["comment"] = data["comment"].str.replace("odk", "data imported from odk", regex=False)
        # Try to parse the date to fail properly if date format is invalid
        try:
            data["field_date"] = pd.to_datetime(data["today"]).dt.strftime("%d.%m.%Y")
        except:
            self.log("Could not parse dates in column 'today' - check the format.")
            messagebox.showerror(title="Could not process CSV file", message="Invalid dates in column 'today'.")
            return None
        # TODO this is not actually a very good solution to that problem. If Pergamon will not care about
        # the dates being incorrect, we could just coerce and add invalid dates as empty strings to the
        # import files?
      
        # Build the import DataFrame according to the columns iDAI.fields csv-Import is expecting: 
        # identifier = unique name, relations.isRecordedIn = Trench/Operation, 
        # scanCode = QR-Code, date.value/date.endValue/date.isRange = the date,
        # amount = number of finds/fragments, spatialLocation = description of the spatial 
        # location (here: additional information about the geometry and find circumstances)
        # category = the category of resource to import (will be used to split into multiple files)
        field_data = pd.DataFrame({
            "relations.isRecordedIn": "Survey Import",
            "identifier": data["find_id"],
            "scanCode": data["find_id"],
            "date.value": data["field_date"],
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

    def save_csv_output(self, field_data, duplicates, output_dir):
        # Since iDAI.field needs one file for each category it will import, we are saving a new csv-File 
        # for each category present in the data. If there are rows with duplicates, 
        # these are saved in a specific "duplicates" file for manual review and merging. 
        # The files are named so that iDAI.field will automatically recognize the category from the file name. 
        self.log(f"Writing output files to directory: {output_dir}")

        selected_date = pd.to_datetime(self.date_picker.get_date())
        selected_date = selected_date.strftime("%Y-%m-%d")


        for category in field_data["category"].dropna().unique():
            this_cat = field_data.loc[
                field_data["category"] == category, field_data.columns != "category"
            ].dropna(subset=["identifier"])

            filename = f'{selected_date}_import.{category}.csv'
            filename_duplicates = f'{selected_date}_duplicates.{category}.csv'


            if not this_cat.empty:
                dupl_idx = this_cat["identifier"].isin(duplicates.index)
                if dupl_idx.any():
                    self.log(f"Writing {len(this_cat.loc[~dupl_idx])} resources to file '{filename}'")
                    this_cat.loc[~dupl_idx].to_csv(f'{output_dir}/{filename}', index=False)
                    self.log(f"Writing {len(this_cat.loc[dupl_idx])} resources to file '{filename_duplicates}'")
                    this_cat.loc[dupl_idx].to_csv(f'{output_dir}/{filename_duplicates}', index=False)
                else:
                    self.log(f"Writing {len(this_cat)} resources to file '{filename}'")
                    this_cat.to_csv(f'{output_dir}/{filename}', index=False)


    def save_geodata(self, data, output_dir):
        # We cannot have empty identifiers in the out GeoJSON, since Field Desktop won't be able to import
        # a FeatureCollection that does not contain valid 'identifier'-attributes. Rows without geodata are 
        # removed for obvious reasons.
        valid_rows = (
            data["find_id"].notna() &  # Not NaN/None
            (data["find_id"] != "") &   # Not empty string
            data["geopoint-Longitude"].notna() & 
            data["geopoint-Latitude"].notna()
        )
        # We select the appropriate columns for the GeoJSON import, for which we only need the point coordinates and 
        # the find_id. We rename find_id to identifier as iDAI.field needs a property of that name for
        # import. 
        geodata = data.loc[valid_rows, ["geopoint-Longitude", "geopoint-Latitude", "find_id"]]
        geodata = geodata.rename(columns={"find_id": "identifier"})
        
        geodata = gpd.GeoDataFrame(
            geodata,
            geometry=[Point(xy) for xy in zip(geodata["geopoint-Longitude"], geodata["geopoint-Latitude"])],
            crs="EPSG:4326"
        )
        geodata = geodata.to_crs(epsg=32635)
        # We can remove the original geodata from the attributes; it makes the file larger and these attributes 
        # cannot be imported by iDAI.field anyway. 
        geodata = geodata.drop(columns=["geopoint-Longitude", "geopoint-Latitude"])
        # An open question is whether we want to import the Altitude as well. It is recorded, but GPS altitude is 
        # very much inaccurate. 
        selected_date = pd.to_datetime(self.date_picker.get_date())
        selected_date = selected_date.strftime("%Y-%m-%d")
        filename = f'{selected_date}_import.Points.geojson'

        self.log(f"Writing output files to directory: {output_dir}")
        self.log(f"Writing {len(geodata)} resources to file '{filename}'")
        geodata.to_file(f"{output_dir}/{filename}", driver="GeoJSON")


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

        # Here, we select the content of the csv file by the date selected in the date picker. 
        # This allows imports of only a single day. 
        self.log(f"Filtering for date: {self.date_picker.get_date()}")
        data = self.filter_by_date(data)
        if data is None: 
            self.log(f"Processing cancelled - no data on that date.")
            return
        
        # We reassign here as the original data is being changed, with a new category-key being added. 
        # If mapping the find_type to the pre-defined categories goes wrong, we exit gracefully so that
        # the user can fix the file manually and try again. 
        data = self.map_categories(data)
        if data is None: 
            self.log(f"Processing cancelled")
            return

        # Am unsure if this is needed - Field Desktop itself does warn when trying to input multiple
        # 'find_id's, but I still see value in notifying people here. 
        duplicates = self.find_duplicates(data)
        
        # Last step in the transformation, we build the new dataframe in the format iDAI.field expects:
        field_data = self.build_field_data(data)
        if field_data is None:
            self.log(f"Processing cancelled")
            return
        # TODO needs error handling and clear communication about malformed input file.

        output_dir = self.select_output_directory()
        try: 
            self.save_csv_output(field_data, duplicates, output_dir)
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
