# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Maybe pyinstaller is unable to get these dependencies; I think it did. But it can't hurt.
hiddenimports = []
hiddenimports += collect_submodules('geopandas')
hiddenimports += collect_submodules('pyproj')
hiddenimports += collect_submodules('shapely')

# gdal is not native python and pyinstaller probably can't bundle this at all.
datas = []
datas += collect_data_files('osgeo') 
datas += collect_data_files('pyproj')

a = Analysis(
    ['src/odk_to_field_extended.py'],
    pathex=[],
    binaries=[],
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
