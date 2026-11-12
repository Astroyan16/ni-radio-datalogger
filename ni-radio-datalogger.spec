# -*- mode: python ; coding: utf-8 -*-
"""Exécutable Windows autonome. À construire avec Python 3.12 x64."""
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

root = Path(SPECPATH)
# Ne pas collecter les DLL d'autres logiciels présents dans le PATH du poste.
# En particulier, une copie étrangère de ucrtbase.dll peut casser l'import Qt.
windows = Path(os.environ["SystemRoot"])
os.environ["PATH"] = os.pathsep.join([
    str(Path(sys.executable).parent), sys.base_prefix,
    str(Path(sys.base_prefix) / "DLLs"), str(windows / "System32"), str(windows),
])
# nidaqmx utilise importlib.metadata.version() dès son import.
datas = copy_metadata("nidaqmx", recursive=True)
datas += collect_data_files("pyqtgraph")

analysis = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=["nidaqmx._library_interpreter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "matplotlib", "scipy", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="NI-Radio-Datalogger-0.1.1-windows-x64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    version=str(root / "packaging" / "windows-version.txt"),
)
