"""Configuracao de logging do SpeechScribe.

Escreve em arquivo (com rotacao simples) e no console.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Pasta de logs: ao lado do executavel (PyInstaller) ou do repositorio (dev)
if getattr(sys, "frozen", False):
    DATA_DIR = Path(sys.executable).resolve().parent.parent
else:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent

LOG_DIR = DATA_DIR / "data" / "logs"
LOG_FILE = LOG_DIR / "speechscribe.log"

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO, log_file: Path | str = LOG_FILE) -> None:
    """Configura logging raiz com arquivo rotativo + console."""
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Evita duplicar handlers se chamado mais de uma vez
    if root.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Arquivo rotativo (mantem 5 arquivos de 1 MB cada)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    logging.getLogger("ctranslate2").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.getLogger("speechscribe").info("Logging inicializado")
