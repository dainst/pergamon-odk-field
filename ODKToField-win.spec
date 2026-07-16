# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('geopandas')
hiddenimports += collect_submodules('pyogrio')
hiddenimports += collect_submodules('shapely')

# A GDAL installation has to be present in the osgeo-directory in this repo.
# https://stackoverflow.com/questions/48210090/how-to-use-bundled-program-after-pyinstaller-add-binary ?

a = Analysis(
    ['src/odk_to_field_extended.py'],
    pathex=[],
    binaries='osgeo\gdal.dll;gdal'
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ODKToField_v0.1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
