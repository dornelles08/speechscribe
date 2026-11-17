# SpeechScribe

Gravação e transcrição de voz ao vivo para `.txt`, `.wav` e `.json`, com interface desktop em PySide6 e modelo Whisper.

## Recursos

- Gravação ao vivo com transcrição simultânea (provisório e definitivo)
- Formas de onda e medidor de nível em tempo real
- Salvamento automático de `.txt`, `.wav` e `.json` com carimbo de data/hora
- Tela de configurações (microfone, modelo Whisper, idioma, pasta de saída, precisão, threads, beam size)
- Logs em arquivo e console
- Auto-atualização via GitHub Releases
- Builds multiplataforma:
  - Linux: AppImage, `.deb`, `.rpm`
  - macOS: `.app`, `.dmg`
  - Windows: `.exe`

## Requisitos

- Python 3.9+
- PySide6
- faster-whisper
- numpy
- sounddevice
- requests

## Instalação (desenvolvimento)

```bash
git clone https://github.com/seu-usuario/speechscribe.git
cd speechscribe
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou .venv\Scripts\activate  # Windows

pip install -r requirements.txt
python -m speechscribe
```

## Build executável

```bash
pip install -r requirements-build.txt
pyinstaller build/speechscribe.spec
```

Os artefatos ficam em `dist/`.

## CI/CD

A cada push na branch `main`, o GitHub Actions gera releases para Linux, macOS e Windows.

## Licença

MIT
