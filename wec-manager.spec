# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for WEC Endurance Manager desktop build.

Build (from project root, with pyinstaller installed):
    pyinstaller wec-manager.spec

Output: dist/WEC-Endurance-Manager/WEC-Endurance-Manager.exe
"""
import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = os.path.abspath(SPECPATH)

hiddenimports = (
    collect_submodules("flask")
    + collect_submodules("jinja2")
    + collect_submodules("apscheduler")
    + [
        "app",
        "admin",
        "assets",
        "attributes",
        "cache",
        "contracts",
        "difficulty",
        "draft",
        "fetcher",
        "game",
        "gm_personalities",
        "injuries",
        "names",
        "news",
        "news_templates",
        "paths",
        "ratings",
        "roster",
        "scheduler",
        "season",
        "season_store",
        "simulation",
        "trade",
        "wec_data",
        "year_end_report",
    ]
)

a = Analysis(
    ["launcher.py"],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "templates"), "templates"),
        (os.path.join(ROOT, "static"), "static"),
        (os.path.join(ROOT, "data", "grid.json"), "data"),
        (os.path.join(ROOT, "data", "names.json"), "data"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gunicorn", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WEC-Endurance-Manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WEC-Endurance-Manager",
)
