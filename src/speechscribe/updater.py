"""Auto-atualizacao via GitHub Releases.

Consulta a API do GitHub para verificar se ha uma versao mais nova e avisa
a interface com um link para download.
"""

from __future__ import annotations

import logging
import sys
from PySide6.QtCore import QObject, QThread, Signal, Slot
import requests

from . import __version__

logger = logging.getLogger("speechscribe")

GITHUB_REPO = "dornelles/speechscribe"  # ajuste para o seu usuario/organizacao


def sys_platform():
    return sys.platform


class Updater(QObject):
    """Verifica atualizacoes em segundo plano e emite sinal se houver uma nova versao."""

    update_available = Signal(str, str)  # versao, url_do_asset
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = QThread(self)
        self.moveToThread(self._thread)
        self._thread.start()

    @Slot()
    def check(self):
        """Dispara a verificacao na thread do updater."""
        self._fetch()

    def _fetch(self):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            logger.debug("Nao foi possivel contatar o GitHub: %s", e)
            return

        data = resp.json()
        latest = data.get("tag_name", "").lstrip("v")
        if not latest:
            return

        if self._newer(latest, __version__):
            assets = data.get("assets", [])
            asset_url = ""
            plat = sys_platform()
            for a in assets:
                name = a.get("name", "").lower()
                if plat.startswith("win") and name.endswith(".exe"):
                    asset_url = a.get("browser_download_url", "")
                    break
                if plat == "darwin" and name.endswith(".dmg"):
                    asset_url = a.get("browser_download_url", "")
                    break
                if plat.startswith("linux") and (name.endswith(".AppImage") or name.endswith(".deb")):
                    asset_url = a.get("browser_download_url", "")
                    break
            if not asset_url and assets:
                asset_url = assets[0].get("browser_download_url", "")
            if asset_url:
                self.update_available.emit(latest, asset_url)

    @staticmethod
    def _newer(latest: str, current: str) -> bool:
        """Comparacao simples de versao semantica (x.y.z)."""
        try:
            l = tuple(int(x) for x in latest.split("."))
            c = tuple(int(x) for x in current.split("."))
            return l > c
        except Exception:
            return latest != current
