"""Entry point para execucao congelada (PyInstaller).

Usa import absoluto para funcionar quando o app e congelado,
pois o PyInstaller executa o script diretamente nao como modulo do pacote.
"""

from speechscribe.app import main

if __name__ == "__main__":
    raise SystemExit(main())
