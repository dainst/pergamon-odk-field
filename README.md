# pergamon-odk-field -- Python Script for Field Desktop Integration of Data from ODK

This repository contains a script that facilitates the import of archaeological data collected using OpenDataKit (ODK) into the [Field Desktop database](https://github.com/dainst/idai-field). It was developed for the Pergamon Micro-Region Survey Project but is provided here as a reusable template and workflow example for other survey projects.

Two scripts are supplied in the reposity. The extended script is released as an executable. It processes and transforms data as exported from the Pergamon Micro-Region Survey Project ODK instance, and saves it in `csv` and `GeoJSON` formats suitable for import into Field Desktop (based on the Project Configuration of the Pergamon Excavation). Only rows that have a 'find_id' (i.e. finds which will be handed over to find processing) are processend. 'find_type' values are replaced with the corresponding categories in Field Desktop, coordinates are transformed from WGS 84 (EPSG: 4326) to WGS 84 UTM Zone 35N (EPSG: 32635), and duplicate 'find_id's are noted and separated. 

The workflow including a supplement is published as `B. Ludwig, L. Steinmann, N. Neuenfeld, Structured Data Collection in Archaeological Surveys. The Use of OpenDataKit (ODK) in the Pergamon Micro-Region (Western Türkiye), FdAI, 2026.`

```bibtex
@article{
  title = {Structured Data Collection in Archaeological Surveys. The Use of OpenDataKit (ODK) in the Pergamon Micro-Region (Western Türkiye)},
  author = {Ludwig, Bernhard and Neuenfeld, Nicole and Steinmann, Lisa},
  journaltitle = {Forum for Digital Archaeology and Infrastructure},
  year = {2026},
  issn = {2748-8861},
  doi = {tba},
  url = {tba}
}
```

# Note

The Python scripts are provided as templates for adaptation and will require modifications for different survey designs or project configurations.

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
python3 src/odk_to_field_basic.py

# Or: run the extended script
python3 src/odk_to_field_extended.py
```

The simple transformer script `odk_to_field_basic.py` is meant as a basic introduction for beginners: Here you can more easily add and remove functionality, or change how and what data is processed, without the need to understand as much about python programming. 

The "new" version (`odk_to_field_extended.py`) is designed for use within the workflow and geared more towards a better user experience at the cost of being less easy to understand from a scripting perspective. This is the version that is released as an executable. 

# Development

To build the standalone executable on your operating system of choice run the following: 
```python 
# add pyinstaller to your venv (note: it is only used for building the executable and thus not in the requirements.txt)
pip install pyinstaller
# For Linux: 
pyinstaller --onefile --windowed --collect-submodules pyogrio --name "ODKToField_v1.0.0" src/odk_to_field_extended.py 
```

On windows, the exe will not be able to transform coordinate systems, since this would require packaging GDAL in this script. You can
still build a windows executable with: 
Then: 
```python  
pyinstaller ODKToField-win 
```
The executable (for your current operating system) will be located in `/dist/`. Remember to update the version number accordingly for each release. 

# Further Information
For more details about the Pergamon project and ongoing research activities, please consult the following resources:

- [DAI Homepage – Pergamon Project](https://www.dainst.org/forschung/projekte/noslug/2858)
- [TransPergMicro Blog](https://www.dainst.blog/transpergmikro/)

For more information about iDAI.field / Field Desktop see:
- [field.idai.world - Online Publications](https://field.idai.world)
- [iDAI.field on GitHub](https://github.com/dainst/idai-field)

For questions about this repository and workflow, please contact:

Bernhard Ludwig, Lisa Steinmann, Nicole Neuenfeld