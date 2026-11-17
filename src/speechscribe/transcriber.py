"""Transcritor Whisper configuravel (idioma, modelo, dispositivo, precisao).

Wrapper sobre faster-whisper que expoe uma interface simples para o Worker.
"""

from __future__ import annotations

import numpy as np

# Import vcommon local (mesmo pacote)
from .voice.vcommon import Transcriber as VCTranscriber


class Transcriber(VCTranscriber):
    """O Transcriber do vcommon fixa portugues; aqui o idioma e configuravel.

    device/compute/threads/beam sao repassados ao WhisperModel do vcommon
    (cuda/cpu, float16/int8, threads de CPU e beam size).
    """

    def __init__(self, size="large-v3-turbo", lang="pt", device="auto",
                 compute="auto", threads=None, beam=1):
        super().__init__(size, device=device, compute=compute, threads=threads, beam=beam)
        self.lang = lang
        self.beam = beam

    def transcribe(self, wav):
        segs, _ = self.model.transcribe(
            np.asarray(wav, dtype=np.float32),
            language=self.lang or None,
            beam_size=self.beam,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segs).strip()
