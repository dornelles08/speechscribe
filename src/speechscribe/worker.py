"""Worker de transcricao: microfone + VAD + Whisper, rodando em QThread separada.

Nunca trava a interface. A interface so envia pedidos por sinais e recebe
resultados por sinais.
"""

from __future__ import annotations

import time
from collections import deque

import numpy as np

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from .voice import vcommon as vc
from .transcriber import Transcriber
from .session import Session

MODELS = ("tiny", "base", "small", "large-v3-turbo")
DEFAULT_MODEL = "large-v3-turbo"
DEFAULT_LANG = "pt"
SILENCE_END = 0.7
MAX_SEGMENT_S = 15.0
PARTIAL_EVERY = 1.2
POLL_MS = 20
WAVE_SECONDS = 4.0


class Stt(QObject):
    """Thread so para o Whisper: o loop do microfone nunca espera por ele.

    - commit (fechar um trecho): fila FIFO, nunca e descartado;
    - partial (texto provisorio): so o mais recente vale.
    """

    ready = Signal(str)
    error = Signal(str)
    busy = Signal(bool)
    partial_ready = Signal(int, str)
    segment_ready = Signal(int, str, float, float)
    commit_done = Signal(int)
    selftest_done = Signal()

    def __init__(self, model_size, lang, device="auto", compute="auto",
                 threads=None, beam=1):
        super().__init__()
        self.model_size = model_size
        self.lang = lang
        self.device = device
        self.compute = compute
        self.threads = threads
        self.beam = beam
        self._stt = None
        self._timer = None
        self._commits = deque()
        self._pending_partial = None
        self._busy = False
        self._paused = False

    # ------------------------------------------------------------ enfileirar
    def submit_partial(self, seg_id, audio):
        self._pending_partial = (seg_id, audio)

    def submit_commit(self, job_id, seg_id, audio, start, end):
        if self._pending_partial is not None and self._pending_partial[0] == seg_id:
            self._pending_partial = None
        self._commits.append((job_id, seg_id, audio, start, end))

    @Slot()
    def start(self):
        try:
            self._stt = Transcriber(
                self.model_size, self.lang, self.device, self.compute,
                self.threads, self.beam,
            )
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"Falha ao carregar o modelo Whisper: {e}")
            return
        self.ready.emit(self.model_size)
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._drain)
        self._timer.start()

    @Slot(str)
    def load_model(self, size):
        if self._busy or self._paused or size == self.model_size:
            return
        self._paused = True
        try:
            stt = Transcriber(size, self.lang, self.device, self.compute,
                              self.threads, self.beam)
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"Falha ao carregar o modelo Whisper: {e}")
            self._paused = False
            return
        self._stt, self.model_size = stt, size
        self._paused = False
        self.ready.emit(size)

    @Slot()
    def shutdown(self):
        if self._timer is not None:
            self._timer.stop()

    @Slot()
    def transcribe_selftest(self):
        try:
            self._stt.transcribe(np.zeros(vc.SR, np.float32))
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"selftest: {e}")
        finally:
            self.selftest_done.emit()

    # ------------------------------------------------------------ processar
    @Slot()
    def _drain(self):
        """Pega no maximo um trabalho (commit tem prioridade sobre partial) e roda."""
        if self._busy or self._paused or self._stt is None:
            return
        if self._commits:
            job_id, seg_id, audio, start, end = self._commits.popleft()
            kind = "commit"
        elif self._pending_partial is not None:
            seg_id, audio = self._pending_partial
            start = end = 0.0
            self._pending_partial = None
            kind = "partial"
        else:
            return

        self._busy = True
        self.busy.emit(True)
        try:
            text = self._stt.transcribe(audio)
        except Exception as e:  # noqa: BLE001
            self.error.emit(f"Falha na transcricao: {e}")
            text = ""
        self._busy = False

        if kind == "commit":
            self.segment_ready.emit(seg_id, text, start, end)
            self.commit_done.emit(job_id)
        else:
            self.partial_ready.emit(seg_id, text)

        if not self._commits and self._pending_partial is None:
            self.busy.emit(False)


class Worker(QObject):
    """Vive numa QThread: microfone + VAD + Whisper. Nunca trava a interface."""

    status = Signal(str)
    ready = Signal(str)
    error = Signal(str)
    level = Signal(float, bool)
    wave = Signal(object)
    partial = Signal(str)
    segment = Signal(str)
    saved = Signal(dict)
    stats = Signal(dict)

    def __init__(self, device=None, model=DEFAULT_MODEL, lang=DEFAULT_LANG,
                 out_dir=None):
        super().__init__()
        self.device = device
        self.model_size = model
        self.lang = lang
        self.out_dir = out_dir
        self.open_mic = True
        self.recording = False
        self.session = None
        self.mic = None
        self.stt = None
        self.det = None
        self._timer = None
        self._seg_start = None
        self._seg_id = 0
        self._last_t = None
        self._last_partial = 0.0
        self._partial_in_flight = False
        self._job_seq = 0
        self._last_job = None
        self._jobs_done = set()
        self._rolling = np.zeros(int(vc.SR * WAVE_SECONDS), np.float32)

    # ------------------------------------------------------------ ciclo de vida
    @Slot()
    def setup(self):
        self.det = vc.UtteranceDetector(
            end_silence=SILENCE_END, max_seconds=MAX_SEGMENT_S
        )
        if self.open_mic:
            try:
                self.mic = vc.Mic(self.device)
            except SystemExit as e:
                self.error.emit(str(e))
                self.ready.emit(self.model_size)
                return
        self.ready.emit(self.model_size)
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @Slot()
    def shutdown(self):
        if self._timer is not None:
            self._timer.stop()
        if self.recording:
            self.stop_rec()
        if self.mic is not None:
            self.mic.close()
            self.mic = None

    # ------------------------------------------------------------ gravacao
    @Slot()
    def start_rec(self):
        if self.recording or self.mic is None or self.stt is None:
            return
        self.session = Session(self.out_dir, self.model_size, self.lang)
        self.session.open()
        self.det.reset()
        self._seg_start = None
        self._seg_id = 0
        self._last_t = None
        self._last_partial = 0.0
        self._partial_in_flight = False
        self._last_job = None
        self._jobs_done = set()
        self.recording = True
        self.status.emit("Gravando")
        self.stats.emit({"recording": True, "elapsed": 0.0, "words": 0})

    @Slot()
    def stop_rec(self):
        if not self.recording:
            return
        self.recording = False
        self._partial_in_flight = False
        self._commit_pending()
        self._seg_start = None
        if self._last_job is None or self._last_job in self._jobs_done:
            self._finalize_session()
        else:
            self.status.emit("Finalizando...")
            # o btn_rec e desabilitado pela MainWindow em _on_status("Finalizando...")

    @Slot(object)
    def set_device(self, device):
        if self.recording:
            return
        if self.mic is not None:
            self.mic.close()
            self.mic = None
        try:
            self.mic = vc.Mic(device)
        except SystemExit as e:
            self.error.emit(str(e))
            return
        self.ready.emit(self.model_size)

    # ------------------------------------------------------------ resultados do Whisper
    @Slot(int, str)
    def _on_partial_ready(self, seg_id, text):
        if seg_id == self._seg_id and self.recording:
            self.partial.emit(text)
        self._partial_in_flight = False

    @Slot(int, str, float, float)
    def _on_segment_ready(self, seg_id, text, start, end):
        if self.session is not None and text.strip():
            self.session.add(text, start, end)
            self.segment.emit(text)
        if seg_id == self._seg_id:
            self.partial.emit("")
        self._partial_in_flight = False

    @Slot(int)
    def _on_commit_done(self, job_id):
        self._jobs_done.add(job_id)
        if (
            not self.recording
            and self._last_job is not None
            and self._last_job in self._jobs_done
            and self.session is not None
        ):
            QTimer.singleShot(0, self._finalize_session)

    # ------------------------------------------------------------ loop
    @Slot()
    def _poll(self):
        blocks = self.mic.blocks() if self.mic is not None else []
        joined = np.concatenate([b for _, b in blocks]) if blocks else None
        if joined is not None:
            n = min(len(joined), len(self._rolling))
            self._rolling = np.concatenate(
                [self._rolling[n:], joined[-n:].astype(np.float32)]
            )
            self.wave.emit(joined)
            rms = float(np.sqrt(np.mean(joined ** 2)))
        else:
            rms = 0.0

        if self.recording and blocks:
            last_t = blocks[-1][0]
            self._last_t = last_t
            for _, b in blocks:
                self.session.audio(b)
                self.det.feed(b)
            if self.det.active:
                if self._seg_start is None:
                    self._seg_start = last_t - len(self.det.buf) * vc.FRAME_S
                    self._seg_id += 1
                    self._partial_in_flight = False
                self._maybe_partial()
            if self.det.done:
                self._submit_commit(
                    self.det.audio, self._seg_start, last_t - self.det.silence
                )
                self.det.reset()
                self._seg_start = None

        self.level.emit(rms, rms > vc.ENERGY_MIN)
        if self.recording and self.session is not None:
            self.stats.emit(
                {
                    "recording": True,
                    "elapsed": time.time() - self.session.t0,
                    "words": self.session.words,
                }
            )

    def _maybe_partial(self):
        """Enfileira o texto provisorio - nunca bloqueia o loop esperando o Whisper."""
        if self._partial_in_flight:
            return
        if len(self.det.buf) * vc.FRAME_S < 0.8:
            return
        now = time.time()
        if now - self._last_partial < PARTIAL_EVERY:
            return
        self._last_partial = now
        audio = np.concatenate(self.det.buf).astype(np.float32)
        self._partial_in_flight = True
        self.stt.submit_partial(self._seg_id, audio)

    def _submit_commit(self, audio, start_abs, end_abs):
        """Enfileira a transcricao definitiva de um trecho."""
        if audio is None or len(audio) < int(0.4 * vc.SR) or self.session is None:
            return None
        t0 = self.session.t0
        start = (
            (start_abs - t0)
            if start_abs is not None
            else (end_abs - t0 - len(audio) / vc.SR)
        )
        end = max(start, end_abs - t0)
        job_id = self._job_seq
        self._job_seq += 1
        self._last_job = job_id
        self.stt.submit_commit(job_id, self._seg_id, audio, max(0.0, start), end)
        self._partial_in_flight = False
        return job_id

    def _commit_pending(self):
        """Fecha o trecho que ainda estava aberto quando o usuario parou."""
        if self.det.active and self.det.buf:
            audio = np.concatenate(self.det.buf).astype(np.float32)
            end = self._last_t if self._last_t is not None else time.time()
            return self._submit_commit(audio, self._seg_start, end)
        return None

    def _finalize_session(self):
        """Fecha a sessao de gravacao (.wav/.txt/.json) e libera a UI."""
        paths = self.session.close() if self.session else None
        self.session = None
        self.det.reset()
        self.status.emit("Salvo")
        if paths:
            self.saved.emit(paths)
        self.stats.emit({"recording": False, "elapsed": 0.0, "words": 0})
