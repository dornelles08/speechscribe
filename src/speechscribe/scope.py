"""Forma de onda dos ultimos segundos + medidor de nivel, desenhados no Qt."""

from __future__ import annotations

import numpy as np

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .voice import vcommon as vc

WAVE_SECONDS = 4.0


class Scope(QWidget):
    """Forma de onda dos ultimos segundos + medidor de nivel."""

    def __init__(self):
        super().__init__()
        self.buf = np.zeros(int(vc.SR * WAVE_SECONDS), np.float32)
        self.rms, self.speaking, self.recording = 0.0, False, False
        self.setMinimumHeight(110)

    @Slot(object)
    def push(self, samples):
        n = min(len(samples), len(self.buf))
        if n > 0:
            self.buf = np.concatenate([self.buf[n:], samples[-n:].astype(np.float32)])
            self.update()

    @Slot(float, bool)
    def set_level(self, rms, speaking):
        self.rms, self.speaking = rms, speaking
        self.update()

    def set_recording(self, on):
        self.recording = on
        self.update()

    def paintEvent(self, _event):  # noqa: N802 (API do Qt)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1a1d22"))
        p.drawRoundedRect(r, 10, 10)

        inner = r.adjusted(10, 10, -10, -30)
        mid = inner.center().y()
        p.setPen(QPen(QColor("#2a2f37"), 1))
        p.drawLine(inner.left(), mid, inner.right(), mid)

        if inner.width() > 0:
            step = max(1, len(self.buf) // inner.width())
            if self.recording:
                color = QColor("#3fb950") if self.speaking else QColor("#2f8f43")
            else:
                color = QColor("#5b6472")
            p.setPen(QPen(color, 1))
            for x in range(inner.width()):
                chunk = self.buf[x * step : (x + 1) * step]
                if chunk.size == 0:
                    continue
                amp = int(
                    min(1.0, float(np.abs(chunk).max()) * 4) * (inner.height() / 2)
                )
                p.drawLine(inner.left() + x, mid - amp, inner.left() + x, mid + amp)

        meter = r.adjusted(10, r.height() - 18, -10, -10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#232830"))
        p.drawRoundedRect(meter, 4, 4)
        if meter.width() > 0:
            frac = float(np.clip((20 * np.log10(self.rms + 1e-6) + 60) / 60, 0, 1))
            if frac > 0:
                bar = meter.adjusted(0, 0, -int((1 - frac) * meter.width()), 0)
                p.setBrush(QColor("#3fb950" if frac < 0.75 else "#e5484d"))
                p.drawRoundedRect(bar, 4, 4)
