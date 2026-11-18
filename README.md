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

uv sync
uv run -m speechscribe
```

Para adicionar uma nova dependência:

```bash
uv add <pacote>
```

Para rodar os testes:

```bash
uv sync --extra dev
uv run pytest tests/
```

## Build executável

```bash
unset VIRTUAL_ENV
uv run pyinstaller build/speechscribe.spec
```

Os artefatos ficam em `dist/`.

Os modelos Whisper **não são empacotados** no instalador (seriam centenas de MBs a vários GBs). Eles são baixados automaticamente do Hugging Face na primeira execução do app, de acordo com o modelo selecionado nas configurações.

## CI/CD

A cada push na branch `main`, o GitHub Actions gera releases para Linux, macOS e Windows.

## Licença

MIT
