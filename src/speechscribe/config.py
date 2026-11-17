"""Gerenciamento de configuracoes do SpeechScribe.

As configuracoes sao salvas em settings.json na pasta de dados do app
(ao lado do executavel (PyInstaller) ou em src/ em modo desenvolvimento).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Pasta de dados: ao lado do executavel (PyInstaller) ou do repositorio (dev)
if getattr(sys, "frozen", False):  # executavel congelado pelo PyInstaller
    DATA_DIR = Path(sys.executable).resolve().parent.parent
else:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent

SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "model": "large-v3-turbo",
    "lang": "pt",
    "device": None,  # None = microfone padrao
    "whisper_device": "auto",
    "whisper_compute": "auto",
    "whisper_threads": None,
    "whisper_beam": 1,
    "out_dir": str(DATA_DIR / "data" / "transcricoes"),
    "silence_end": 0.7,
    "max_segment_s": 15.0,
    "theme": "dark",
    "check_updates": True,
    "save_txt": True,      # salvar arquivo final da transcricao (.txt)
    "save_segments": True, # salvar segmentos da transcricao (.json)
}


class Config:
    """Carrega e salva configuracoes em JSON."""

    def __init__(self, path: Path | str = SETTINGS_PATH):
        self.path = Path(path)
        self._data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data.update(raw)
            except Exception:  # arquivo corrompido: mantem padroes
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
