# pergamon-odk-field -- Python Script for Field Desktop Integration of Data from ODK

This repository contains a script that facilitates the import of archaeological data collected using OpenDataKit (ODK) into the [Field Desktop database](https://github.com/dainst/idai-field). It was developed for the Pergamon Micro-Region Survey Project but is provided here as a reusable template and workflow example for other survey projects.

Python Script (.py) – A script to process and transform ODK data for import into Field Desktop, including filtering by find type, generating CSV files for each category, converting coordinates from WGS 84 (EPSG: 4326) to WGS 84 UTM Zone 35N (EPSG: 32635), and checking for duplicate entries.

The workflow has been published as 

`cite article here`

...


# Note

The Python script is provided as a template for adaptation and may require minor modifications for different survey designs or database schemas.


# Run this Script from the Command Line

To start this script from the command line, use the following commands in your terminal while in the main directory:

```python
# Create package environment
python3 -m venv venv

# Activate your environment
source venv/bin/activate

# Install the required packages in your environment
pip install -r requirements.txt 

# Either: run the simple transformer script
python3 src/odk_to_field.py

# Or: run the extended script
python3 src/new_odk_to_field.py
```

The simple transformer script `odk_to_field.py` is meant as a basic introduction for beginners: Here you can more easily add and remove functionality, or change how and what data is processed, without the need to understand as much about python programming. 

The "new" version (`new_odk_to_field.py`) is designed for use within the workflow and geared more towards a better user experience at the cost of being less easy to understand from a scripting perspective. 


# Further Information
For more details about the Pergamon project and ongoing research activities, please consult the following resources:

[DAI Homepage – Pergamon Project](https://www.dainst.org/forschung/projekte/noslug/2858)
[TransPergMicro Blog](https://www.dainst.blog/transpergmikro/)

For questions or issues, please contact 

Bernhard Ludwig, Lisa Steinmann, Nicole Neuenfeld