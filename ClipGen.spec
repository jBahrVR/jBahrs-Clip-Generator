# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Collect data files
datas = []
try:
    datas += collect_data_files('customtkinter')
except Exception:
    pass

try:
    datas += collect_data_files('whisper')
except Exception:
    pass

if os.path.exists('app_icon.ico'):
    datas.append(('app_icon.ico', '.'))

# Collect hidden imports
hiddenimports = [
    'customtkinter',
    'pystray',
    'pystray._win32',
    'PIL',
    'PIL._tkinter_finder',
    'windnd',
    'torch',
    'whisper',
    'faster_whisper',
    'ctranslate2',
    'tokenizers',
    'huggingface_hub',
    'av',
    'cv2',
    'google.genai',
    'google.genai.models',
    'anthropic',
    'openai',
    'numpy',
    'utils',
    'event_bus',
    'gallery_manager',
    'queue_manager',
    'social_publisher',
    'subtitle_engine',
    'tracking_engine',
    'video_player',
    'model_fetcher',
]
try:
    hiddenimports += collect_submodules('gui')
except Exception:
    pass

binaries = []
try:
    binaries += collect_dynamic_libs('torch')
except Exception:
    pass

try:
    binaries += collect_dynamic_libs('nvidia')
except Exception:
    pass

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest', 'pytest'],
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
    name='jBahrs-Clip-Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='jBahrs-Clip-Generator',
)
