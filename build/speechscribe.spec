# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ["../src/entry_point.py"],
    pathex=["../src"],
    binaries=[],
    datas=[],  # modelos Whisper sao baixados em tempo de execução (huggingface), não empacotados no instalador
    hiddenimports=collect_submodules("speechscribe") + [
        "faster_whisper",
        "ctranslate2",
        "sounddevice",
        "numpy",
        "requests",
        "webrtcvad",
        "torch",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="speechscribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disabled_windowed=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name="SpeechScribe.app",
    info_plist="../build/Info.plist",
    bundle_identifier=None,
)

# Injeta permissao de microfone no Info.plist do .app (macOS exige NSMicrophoneUsageDescription)
import subprocess, os
_plist = os.path.join(os.getcwd(), "dist", "SpeechScribe.app", "Contents", "Info.plist")
if os.path.exists(_plist):
    subprocess.run([
        "/usr/libexec/PlistBuddy",
        "-c",
        "Add :NSMicrophoneUsageDescription string 'O SpeechScribe precisa de acesso ao microfone para gravar e transcrever o que voce fala.'",
        _plist,
    ])
