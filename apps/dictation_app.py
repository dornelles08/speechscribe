"""Compatibilidade: aponta para o novo modulo SpeechScribe.

Mantido para quem ainda referencia apps/dictation_app.py no repositorio original.
"""

from speechscribe.app import main

if __name__ == "__main__":
    raise SystemExit(main())
