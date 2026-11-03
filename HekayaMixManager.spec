# PyInstaller build specification for Hekaya Mix Manager.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("bidi") + collect_submodules("arabic_reshaper")

a = Analysis(
    ["mix_v3.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HekayaMixManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
