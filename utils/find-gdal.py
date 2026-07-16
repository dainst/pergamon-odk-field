
# Hello, this is part of a journey on packaging gdal-dependent libraries
# in an executable. 
# My workaround is based mainly on this 
# https://gis.stackexchange.com/questions/203572/working-standalone-app-exe-from-python3-script-that-imports-osgeo-gdal
# exchange. 
# The gist is that gdal cannot ever be packaged by pyinstaller. You need to package executables/dll for gdal somehow. 
# You can tell pyinstaller about it with this 'data' array or 'binaries'. 
# See also
# https://gis.stackexchange.com/questions/177488/working-windows-standalone-exe-from-qgis-python-script-using-pyinstaller
# And then, crs transformation should theoretically work. 
#
# On Linux, this is not an issue. On linux, everything just works. 
# On Windows, it does not. 
# On MacOS, I did not try, and I will maybe never know. 
#
# I install gdal in the workflow for the runner with 
#   pip install gdal-installer
#   install-gdal
# which tbh is not ideal, it is packaging the Grohl wheel: https://github.com/cgohlke/geospatial-wheels/
# and is a rather small project: https://github.com/celray/python-gdal-installer
# but is was the easiest way. 
# Then, osgeo / gdal actually exists, and we need to figure out where in the runner it is located. 
# Which is why we are looking for the filepath in this little script. 
import osgeo.gdal
print("Does osgeo/gdal exist?")
print(osgeo.gdal.__file__)
# That path is then used in the build.yml, where the directory is copied to the repo-directory.
# (I had to copy it, I don't care why.)
# All the osgeo/gdal exes and dlls will then be in the current directoy (the repo directory)
# in the "osgeo" dir. Which is where the pyinstaller-spec expects them.
# I'm sorry. 
