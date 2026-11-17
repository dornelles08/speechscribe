"""Uma gravacao: escreve .txt e .wav na hora e fecha o .json no final."""

from __future__ import annotations

import json
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from .voice import vcommon as vc


class Session:
    """Uma gravacao: escreve .txt e .wav na hora e fecha o .json no final."""

    def __init__(self, out_dir, model, lang, save_txt=True, save_segments=True):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        base, n = stamp, 1
        while (self.dir / f"{base}.txt").exists():  # duas gravacoes no mesmo segundo
            n += 1
            base = f"{stamp}_{n}"
        self.txt_path = self.dir / f"{base}.txt"
        self.wav_path = self.dir / f"{base}.wav"
        self.json_path = self.dir / f"{base}.json"
        self.model, self.lang = model, lang
        self.t0 = time.time()
        self.segments = []
        self.words = 0
        self.save_txt = save_txt
        self.save_segments = save_segments
        self._txt = None
        self._wav = None

    def open(self):
        if self.save_txt:
            self._txt = self.txt_path.open("w", encoding="utf-8")
        self._wav = wave.open(str(self.wav_path), "wb")
        self._wav.setnchannels(1)
        self._wav.setsampwidth(2)
        self._wav.setframerate(vc.SR)

    def audio(self, block):
        if self._wav is not None:
            pcm = (np.clip(block, -1, 1) * 32767).astype("<i2")
            self._wav.writeframes(pcm.tobytes())

    def add(self, text, start, end):
        text = text.strip()
        if not text:
            return
        self.segments.append(
            {"inicio_s": round(start, 2), "fim_s": round(end, 2), "texto": text}
        )
        self.words += len(text.split())
        if self.save_txt and self._txt is not None:
            self._txt.write(text + "\n")
            self._txt.flush()  # write-through: nada se perde se o app fechar

    def close(self):
        if self._wav is not None:
            self._wav.close()
            self._wav = None
        if self._txt is not None:
            self._txt.close()
            self._txt = None
        data = {
            "inicio": datetime.fromtimestamp(self.t0).isoformat(timespec="seconds"),
            "duracao_s": round(time.time() - self.t0, 2),
            "modelo": self.model,
            "idioma": self.lang,
        }
        if self.save_segments:
            data["segmentos"] = self.segments
        self.json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "txt": str(self.txt_path),
            "wav": str(self.wav_path),
            "json": str(self.json_path),
        }
