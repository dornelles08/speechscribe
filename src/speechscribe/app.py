"""Janela principal do SpeechScribe."""

from __future__ import annotations

import html
import logging
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QMetaObject, QThread, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import Config
from .logging_setup import setup_logging
from .scope import Scope
from .session import Session
from .updater import Updater
from .worker import DEFAULT_MODEL, DEFAULT_LANG, MODELS, Worker
from . import __version__

setup_logging()
logger = logging.getLogger("speechscribe")


class SettingsDialog(QDialog):
    """Tela de configuracoes do SpeechScribe."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Configuracoes - SpeechScribe")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_from_config()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setSpacing(10)

        row = 0

        # Modelo Whisper
        grid.addWidget(QLabel("Modelo Whisper:"), row, 0)
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(MODELS)
        grid.addWidget(self.cmb_model, row, 1)
        row += 1

        # Idioma
        grid.addWidget(QLabel("Idioma:"), row, 0)
        self.edit_lang = QLineEdit()
        self.edit_lang.setPlaceholderText("ex.: pt, en")
        grid.addWidget(self.edit_lang, row, 1)
        row += 1

        # Dispositivo de audio
        grid.addWidget(QLabel("Dispositivo de audio (indice):"), row, 0)
        self.edit_device = QLineEdit()
        self.edit_device.setPlaceholderText("vazio = padrao do sistema")
        grid.addWidget(self.edit_device, row, 1)
        row += 1

        # Dispositivo Whisper
        grid.addWidget(QLabel("Dispositivo Whisper:"), row, 0)
        self.cmb_whisper_device = QComboBox()
        self.cmb_whisper_device.addItems(["auto", "cuda", "cpu"])
        grid.addWidget(self.cmb_whisper_device, row, 1)
        row += 1

        # Precisao Whisper
        grid.addWidget(QLabel("Precisao Whisper:"), row, 0)
        self.cmb_whisper_compute = QComboBox()
        self.cmb_whisper_compute.addItems(["auto", "int8", "int8_float16", "float16", "float32"])
        grid.addWidget(self.cmb_whisper_compute, row, 1)
        row += 1

        # Threads CPU
        grid.addWidget(QLabel("Threads CPU:"), row, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(0, 64)
        self.spin_threads.setSpecialValueText("auto")
        grid.addWidget(self.spin_threads, row, 1)
        row += 1

        # Beam size
        grid.addWidget(QLabel("Beam size:"), row, 0)
        self.spin_beam = QSpinBox()
        self.spin_beam.setRange(1, 10)
        grid.addWidget(self.spin_beam, row, 1)
        row += 1

        # Silencio final (s)
        grid.addWidget(QLabel("Silencio p/ fechar trecho (s):"), row, 0)
        self.spin_silence = QSpinBox()
        self.spin_silence.setRange(1, 1000)
        self.spin_silence.setSuffix(" decimos")  # armazenamos em decimos de segundo
        grid.addWidget(self.spin_silence, row, 1)
        row += 1

        # Duracao maxima trecho (s)
        grid.addWidget(QLabel("Duracao maxima trecho (s):"), row, 0)
        self.spin_max_seg = QSpinBox()
        self.spin_max_seg.setRange(5, 120)
        grid.addWidget(self.spin_max_seg, row, 1)
        row += 1

        # Pasta de saida
        grid.addWidget(QLabel("Pasta de transcricoes:"), row, 0)
        h = QHBoxLayout()
        self.edit_out_dir = QLineEdit()
        self.btn_browse = QPushButton("Escolher...")
        self.btn_browse.clicked.connect(self._browse_out_dir)
        h.addWidget(self.edit_out_dir)
        h.addWidget(self.btn_browse)
        grid.addLayout(h, row, 1)
        row += 1

        # Salvar arquivo final da transcricao (.txt)
        self.chk_save_txt = QCheckBox("Salvar arquivo final da transcricao (.txt)")
        self.chk_save_txt.setToolTip(
            "Desmarque se nao quiser gerar o arquivo de texto da sessao."
        )
        grid.addWidget(self.chk_save_txt, row, 0, 1, 2)
        row += 1

        # Salvar segmentos da transcricao (.json)
        self.chk_save_segments = QCheckBox("Salvar segmentos da transcricao (.json)")
        self.chk_save_segments.setToolTip(
            "Desmarque se nao quiser gerar o JSON com os trechos (inicio/fim/texto)."
        )
        grid.addWidget(self.chk_save_segments, row, 0, 1, 2)
        row += 1

        # Atualizacoes automaticas
        self.chk_updates = QPushButton("Verificar atualizacoes agora")
        self.chk_updates.setCheckable(True)
        self.chk_updates.setChecked(bool(self.config.get("check_updates")))
        grid.addWidget(QLabel("Atualizacoes automaticas:"), row, 0)
        grid.addWidget(self.chk_updates, row, 1)
        row += 1

        lay.addLayout(grid)

        botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._save)
        botoes.rejected.connect(self.reject)
        lay.addWidget(botoes)

    def _browse_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Escolher pasta de transcricoes")
        if d:
            self.edit_out_dir.setText(d)

    def _load_from_config(self):
        self.cmb_model.setCurrentText(self.config.get("model", DEFAULT_MODEL))
        self.edit_lang.setText(self.config.get("lang", DEFAULT_LANG))
        dev = self.config.get("device")
        self.edit_device.setText("" if dev is None else str(dev))
        self.cmb_whisper_device.setCurrentText(self.config.get("whisper_device", "auto"))
        self.cmb_whisper_compute.setCurrentText(self.config.get("whisper_compute", "auto"))
        th = self.config.get("whisper_threads")
        self.spin_threads.setValue(0 if th is None else int(th))
        self.spin_beam.setValue(int(self.config.get("whisper_beam", 1)))
        silence = float(self.config.get("silence_end", 0.7))
        self.spin_silence.setValue(int(round(silence * 10)))
        self.spin_max_seg.setValue(int(self.config.get("max_segment_s", 15.0)))
        self.edit_out_dir.setText(self.config.get("out_dir", ""))
        self.chk_save_txt.setChecked(bool(self.config.get("save_txt", True)))
        self.chk_save_segments.setChecked(bool(self.config.get("save_segments", True)))

    def _save(self):
        self.config.set("model", self.cmb_model.currentText())
        self.config.set("lang", self.edit_lang.text().strip() or DEFAULT_LANG)
        dev_text = self.edit_device.text().strip()
        self.config.set("device", int(dev_text) if dev_text.isdigit() else (None if not dev_text else dev_text))
        self.config.set("whisper_device", self.cmb_whisper_device.currentText())
        self.config.set("whisper_compute", self.cmb_whisper_compute.currentText())
        th = self.spin_threads.value()
        self.config.set("whisper_threads", None if th == 0 else th)
        self.config.set("whisper_beam", self.spin_beam.value())
        self.config.set("silence_end", self.spin_silence.value() / 10.0)
        self.config.set("max_segment_s", float(self.spin_max_seg.value()))
        self.config.set("out_dir", self.edit_out_dir.text().strip())
        self.config.set("save_txt", self.chk_save_txt.isChecked())
        self.config.set("save_segments", self.chk_save_segments.isChecked())
        self.config.set("check_updates", self.chk_updates.isChecked())
        self.config.save()
        self.accept()


class MainWindow(QMainWindow):
    req_start = Signal()
    req_stop = Signal()
    req_device = Signal(object)
    req_model = Signal(str)
    req_selftest = Signal()

    def __init__(
        self,
        device=None,
        model=DEFAULT_MODEL,
        lang=DEFAULT_LANG,
        out_dir=None,
        selftest=False,
        whisper_device="auto",
        whisper_compute="auto",
        whisper_threads=None,
        whisper_beam=1,
    ):
        super().__init__()
        self.setWindowTitle(f"SpeechScribe v{__version__}")
        self.resize(820, 640)
        self.out_dir = Path(out_dir) if out_dir else None
        self._recording = False
        self._closing = False
        self._t0 = 0.0
        self._elapsed_frozen = 0.0
        self._committed = []
        self._partial = ""
        self._ready_mic = False
        self._ready_model = False

        self.config = Config()
        self._apply_config_overrides(device, model, lang, out_dir,
                                     whisper_device, whisper_compute,
                                     whisper_threads, whisper_beam)

        self._build_ui()
        self._populate_devices(self.config.get("device"))
        self._start_worker(
            self.config.get("device"), self.config.get("model"),
            self.config.get("lang"),
            open_mic=not selftest,
            whisper_device=self.config.get("whisper_device"),
            whisper_compute=self.config.get("whisper_compute"),
            whisper_threads=self.config.get("whisper_threads"),
            whisper_beam=self.config.get("whisper_beam"),
        )
        self._on_status(f"Carregando modelo Whisper '{self.config.get('model')}'...")

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(500)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start()

        # Auto-atualizacao
        if self.config.get("check_updates"):
            self.updater = Updater(self)
            self.updater.update_available.connect(self._on_update_available)
            QTimer.singleShot(2000, self.updater.check)

    def _apply_config_overrides(self, device, model, lang, out_dir,
                                whisper_device, whisper_compute,
                                whisper_threads, whisper_beam):
        """Argumentos de linha de comando sobrescrevem o config."""
        if device is not None:
            self.config.set("device", device)
        if model != DEFAULT_MODEL:
            self.config.set("model", model)
        if lang != DEFAULT_LANG:
            self.config.set("lang", lang)
        if out_dir is not None:
            self.config.set("out_dir", out_dir)
        if whisper_device != "auto":
            self.config.set("whisper_device", whisper_device)
        if whisper_compute != "auto":
            self.config.set("whisper_compute", whisper_compute)
        if whisper_threads is not None:
            self.config.set("whisper_threads", whisper_threads)
        if whisper_beam != 1:
            self.config.set("whisper_beam", whisper_beam)

    # ------------------------------------------------------------ interface
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(12)

        top = QHBoxLayout()
        self.pill = QLabel("Iniciando...")
        self.pill.setObjectName("pill")
        top.addWidget(self.pill)
        self.lbl_proc = QLabel("transcrevendo…")
        self.lbl_proc.setObjectName("proc")
        self.lbl_proc.hide()
        top.addWidget(self.lbl_proc)
        top.addStretch(1)
        top.addWidget(QLabel("Microfone"))
        self.cmb_device = QComboBox()
        self.cmb_device.setMinimumWidth(220)
        self.cmb_device.currentIndexChanged.connect(self._on_device)
        top.addWidget(self.cmb_device)
        top.addWidget(QLabel("Modelo"))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(MODELS)
        self.cmb_model.setCurrentText(DEFAULT_MODEL)
        self.cmb_model.currentTextChanged.connect(self._on_model_change)
        top.addWidget(self.cmb_model)
        self.btn_settings = QPushButton("Configuracoes")
        self.btn_settings.clicked.connect(self._open_settings)
        top.addWidget(self.btn_settings)
        lay.addLayout(top)

        self.lbl_download = QLabel("")
        self.lbl_download.setObjectName("download")
        self.lbl_download.setAlignment(Qt.AlignCenter)
        self.lbl_download.hide()
        lay.addWidget(self.lbl_download)

        self.lbl_update = QLabel("")
        self.lbl_update.setObjectName("download")
        self.lbl_update.setAlignment(Qt.AlignCenter)
        self.lbl_update.hide()
        lay.addWidget(self.lbl_update)

        self.scope = Scope()
        lay.addWidget(self.scope)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setObjectName("transcript")
        self._render()
        lay.addWidget(self.text, 1)

        bottom = QHBoxLayout()
        self.btn_rec = QPushButton("GRAVAR")
        self.btn_rec.setObjectName("rec")
        self.btn_rec.setCheckable(True)
        self.btn_rec.clicked.connect(self._toggle)
        self.btn_rec.setEnabled(False)
        bottom.addWidget(self.btn_rec)
        self.btn_open = QPushButton("Abrir pasta")
        self.btn_open.clicked.connect(self._open_folder)
        bottom.addWidget(self.btn_open)
        bottom.addStretch(1)
        self.lbl_info = QLabel("00:00  ·  0 palavras")
        self.lbl_info.setObjectName("info")
        bottom.addWidget(self.lbl_info)
        lay.addLayout(bottom)

        self.hint = QLabel(
            "ESPACO / ENTER = gravar ou parar   |   ESC = sair   |   "
            f"salvando em {self.config.get('out_dir')}"
        )
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self._toggle)
        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self._toggle)
        QShortcut(QKeySequence(Qt.Key_Enter), self, activated=self._toggle)

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.hint.setText(f"salvando em {self.config.get('out_dir')}")
            # Reconecta worker com novo dispositivo se mudou
            dev = self.config.get("device")
            if dev != (self.cmb_device.currentData()):
                self.req_device.emit(dev)

    def _populate_devices(self, device):
        self.cmb_device.addItem("Microfone padrao do sistema", None)
        try:
            import sounddevice as sd

            for i, d in enumerate(sd.query_devices()):
                if d.get("max_input_channels", 0) > 0:
                    self.cmb_device.addItem(f"{i}: {d['name']}", i)
        except Exception:  # noqa: BLE001
            pass
        if device is not None:
            idx = self.cmb_device.findData(device)
            if idx >= 0:
                self.cmb_device.setCurrentIndex(idx)

    def _start_worker(self, device, model, lang, open_mic,
                      whisper_device="auto", whisper_compute="auto",
                      whisper_threads=None, whisper_beam=1):
        # thread do Whisper (transcricao)
        self.stt_thread = QThread(self)
        from .worker import Stt
        self.stt = Stt(model, lang, whisper_device, whisper_compute,
                       whisper_threads, whisper_beam)
        self.stt.moveToThread(self.stt_thread)
        self.stt_thread.started.connect(self.stt.start)

        # thread do microfone
        self.thread = QThread(self)
        self.worker = Worker(
            device, model, lang, self.out_dir or self.config.get("out_dir"),
            save_txt=self.config.get("save_txt", True),
            save_segments=self.config.get("save_segments", True),
        )
        self.worker.open_mic = open_mic
        self.worker.stt = self.stt
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.setup)

        # pedidos da interface -> worker / stt
        self.req_start.connect(self.worker.start_rec)
        self.req_stop.connect(self.worker.stop_rec)
        self.req_device.connect(self.worker.set_device)
        self.req_model.connect(self.stt.load_model)
        self.req_selftest.connect(self.stt.transcribe_selftest)

        # worker -> interface
        self.worker.status.connect(self._on_status)
        self.worker.error.connect(self._on_error)
        self.worker.level.connect(self.scope.set_level)
        self.worker.wave.connect(self.scope.push)
        self.worker.partial.connect(self._on_partial)
        self.worker.segment.connect(self._on_segment)
        self.worker.saved.connect(self._on_saved)
        self.worker.stats.connect(self._on_stats)
        self.worker.ready.connect(self._on_worker_ready)

        # stt -> worker
        self.stt.partial_ready.connect(self.worker._on_partial_ready)
        self.stt.segment_ready.connect(self.worker._on_segment_ready)
        self.stt.commit_done.connect(self.worker._on_commit_done)

        # stt -> interface
        self.stt.ready.connect(self._on_model_ready)
        self.stt.error.connect(self._on_error)
        self.stt.busy.connect(self._on_busy)
        self.stt.selftest_done.connect(self._selftest_done)

        self.stt_thread.start()
        self.thread.start()

    # ------------------------------------------------------------ acoes
    def _toggle(self):
        if self._recording:
            self._stop()
        else:
            self._start()

    def _start(self):
        self._committed, self._partial = [], ""
        self._render()
        self.btn_rec.setChecked(True)
        self.req_start.emit()

    def _stop(self):
        self.btn_rec.setChecked(False)
        self.req_stop.emit()

    def _on_device(self, _idx):
        self.req_device.emit(self.cmb_device.currentData())

    def _open_folder(self):
        out_dir = Path(self.config.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir)))

    # ------------------------------------------------------------ sinais do worker
    def _on_status(self, msg):
        colors = {"Pronto": "#3fb950", "Gravando": "#e5484d", "Salvo": "#3fb950"}
        waiting = msg.startswith(("Carregando", "Finalizando"))
        color = colors.get(msg, "#d0a215" if waiting else "#8b929c")
        self.pill.setText(msg)
        self.pill.setStyleSheet(
            f"background: {color}22; color: {color}; border: 1px solid {color}55;"
            "border-radius: 12px; padding: 4px 14px; font-weight: 600;"
        )
        if msg == "Gravando":
            self._recording, self._t0 = True, time.time()
            self._elapsed_frozen = 0.0
            self.scope.set_recording(True)
            self.btn_rec.setText("PARAR")
            self.cmb_device.setEnabled(False)
            self.cmb_model.setEnabled(False)
            self.btn_settings.setEnabled(False)
        elif msg == "Finalizando...":
            self.btn_rec.setEnabled(False)
            self.cmb_device.setEnabled(False)
            self.cmb_model.setEnabled(False)
            self.btn_settings.setEnabled(False)
            self.scope.set_recording(False)
            self._recording = False
            self._elapsed_frozen = time.time() - self._t0
        elif msg in ("Pronto", "Salvo"):
            self.btn_rec.setEnabled(True)
            self._recording = False
            self._elapsed_frozen = 0.0
            self.scope.set_recording(False)
            self.btn_rec.setText("GRAVAR")
            self.btn_rec.setChecked(False)
            self.cmb_device.setEnabled(True)
            self.cmb_model.setEnabled(True)
            self.btn_settings.setEnabled(True)

    def _on_worker_ready(self, _model=""):
        self._ready_mic = True
        self._maybe_ready()

    def _on_model_ready(self, _model=""):
        self._ready_model = True
        self.lbl_download.hide()
        self._maybe_ready()

    def _maybe_ready(self):
        if self._ready_mic and self._ready_model and not self._recording:
            self.btn_rec.setEnabled(True)
            self._on_status("Pronto")

    def _on_model_change(self, size):
        if not hasattr(self, "stt") or size == self.stt.model_size or self._recording:
            return
        self._ready_model = False
        self.btn_rec.setEnabled(False)
        self.cmb_model.setEnabled(False)
        self.cmb_device.setEnabled(False)
        self.btn_settings.setEnabled(False)
        self.lbl_download.setText(f"Baixando modelo Whisper '{size}'...")
        self.lbl_download.show()
        self._on_status(f"Carregando modelo Whisper '{size}'...")
        self.req_model.emit(size)

    @Slot(bool)
    def _on_busy(self, busy):
        self.lbl_proc.setVisible(bool(busy))

    def _on_error(self, msg):
        low = msg.lower()
        if "microfone" in low or "modelo" in low:
            self.btn_rec.setEnabled(False)
        self.pill.setText("Erro")
        self.pill.setStyleSheet(
            "background: #e5484d22; color: #e5484d; border: 1px solid #e5484d55;"
            "border-radius: 12px; padding: 4px 14px; font-weight: 600;"
        )
        self.lbl_info.setText(msg.splitlines()[0][:120])
        logger.error(msg)
        print(f"[erro] {msg}", file=sys.stderr)

    @Slot(str)
    def _on_partial(self, text):
        self._partial = text
        self._render()

    @Slot(str)
    def _on_segment(self, text):
        self._committed.append(text)
        self._partial = ""
        self._render()

    @Slot(dict)
    def _on_saved(self, paths):
        self.lbl_info.setText(f"{getattr(self, '_words', 0)} palavras")
        self.hint.setText(f"ultimo arquivo: {paths['txt']}")

    @Slot(dict)
    def _on_stats(self, stats):
        if stats.get("recording"):
            self._words = stats.get("words", 0)
        else:
            self._words = len(" ".join(self._committed).split())

    # ------------------------------------------------------------ auto-atualizacao
    @Slot(str, str)
    def _on_update_available(self, version, url):
        self.lbl_update.setText(
            f"Nova versao disponivel: {version}  "
            f"<a href='{url}'>baixar</a>"
        )
        self.lbl_update.setOpenExternalLinks(True)
        self.lbl_update.show()
        logger.info("Nova versao disponivel: %s (%s)", version, url)

    # ------------------------------------------------------------ selftest
    @Slot(str)
    def _selftest_ready(self, _model):
        QTimer.singleShot(300, self.req_selftest.emit)

    @Slot()
    def _selftest_done(self):
        print("selftest: ok (interface + 2 threads + modelo + transcricao)", flush=True)
        self.close()

    # ------------------------------------------------------------ util
    def _render(self):
        blocks = "".join(
            f"<p style='margin:0 0 10px 0'>{html.escape(t)}</p>"
            for t in self._committed
        )
        if self._partial:
            blocks += (
                "<p style='margin:0 0 10px 0;color:#8b929c;font-style:italic'>"
                f"{html.escape(self._partial)}</p>"
            )
        if not blocks:
            blocks = (
                "<p style='color:#5b6472'>Aperte GRAVAR e comece a falar. "
                "O texto aparece aqui enquanto voce fala.</p>"
            )
        self.text.setHtml(blocks)
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _tick(self):
        if self._recording:
            elapsed = time.time() - self._t0
        else:
            elapsed = self._elapsed_frozen
        words = getattr(self, "_words", len(" ".join(self._committed).split()))
        self.lbl_info.setText(
            f"{int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}  ·  {words} palavras"
        )

    def keyPressEvent(self, event):  # noqa: N802 (API do Qt)
        if event.key() == Qt.Key_Escape:
            if self._recording:
                self._stop()
            else:
                self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):  # noqa: N802 (API do Qt)
        if not self._closing:
            self._closing = True
            self._ui_timer.stop()
            QMetaObject.invokeMethod(
                self.worker, "shutdown", Qt.BlockingQueuedConnection
            )
            QMetaObject.invokeMethod(self.stt, "shutdown", Qt.BlockingQueuedConnection)
            self.thread.quit()
            self.thread.wait(5000)
            self.stt_thread.quit()
            self.stt_thread.wait(5000)
        super().closeEvent(event)


STYLE = """
#root { background: #14161a; }
QLabel { color: #cbd2dc; }
QLabel#pill { background: #232830; color: #cbd2dc; border: 1px solid #2f3640;
              border-radius: 12px; padding: 4px 14px; font-weight: 600; }
QLabel#info { color: #8b929c; }
QLabel#proc { color: #d0a215; font-size: 12px; }
QLabel#download { color: #d0a215; font-size: 13px; font-weight: 600; }
QLabel#hint { color: #5b6472; font-size: 11px; }
QTextEdit#transcript { background: #1a1d22; border: 1px solid #2a2f37; border-radius: 10px;
                       color: #e8eaed; font-size: 16px; padding: 12px; }
QComboBox { background: #1d2026; border: 1px solid #2a2f37; border-radius: 8px;
            padding: 5px 10px; color: #dfe3e8; }
QComboBox:hover { border-color: #3a4049; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView { background: #1d2026; color: #dfe3e8; border: 1px solid #2a2f37;
                              selection-background-color: #2f3640; }
QPushButton { background: #232830; border: 1px solid #2f3640; border-radius: 8px;
              padding: 8px 18px; color: #dfe3e8; font-weight: 600; }
QPushButton:hover { background: #2b313a; }
QPushButton#rec { background: #e5484d; border: none; border-radius: 26px;
                  padding: 14px 34px; color: white; font-size: 15px; font-weight: 700; }
QPushButton#rec:hover { background: #f2555a; }
QPushButton#rec:checked { background: #3a3f47; color: #ffb3b6; }
"""


def main():
    import argparse

    p = argparse.ArgumentParser(
        description="SpeechScribe: gravacao e transcricao de voz ao vivo"
    )
    p.add_argument("--device", help="indice ou nome (parcial) do microfone")
    p.add_argument("--list-devices", action="store_true", help="lista os microfones e sai")
    p.add_argument(
        "--model", default=DEFAULT_MODEL, choices=MODELS, help="tamanho do Whisper"
    )
    p.add_argument("--lang", default=DEFAULT_LANG, help="idioma da fala (ex: pt, en)")
    p.add_argument(
        "--whisper-device", choices=("auto", "cuda", "cpu"), default="auto",
        help="onde rodar o Whisper (padrao: auto = tenta a GPU)",
    )
    p.add_argument(
        "--whisper-compute",
        choices=("auto", "int8", "int8_float16", "float16", "float32"),
        default="auto",
        help="precisao do Whisper (padrao: auto = float16 na GPU, int8 na CPU)",
    )
    p.add_argument(
        "--whisper-threads", type=int, default=None,
        help="threads de CPU para o Whisper (padrao: automatico)",
    )
    p.add_argument(
        "--whisper-beam", type=int, default=1,
        help="beam size do Whisper (padrao: 1 = mais rapido)",
    )
    p.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent.parent / "data" / "transcricoes"),
        help="pasta onde salvar as gravacoes",
    )
    p.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args()

    if a.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0

    device = a.device
    if isinstance(device, str) and device.isdigit():
        device = int(device)

    if a.selftest:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    families = QFontDatabase.families()
    family = next(
        (
            f
            for f in ("SF Pro Text", "Helvetica Neue", "Inter", "Segoe UI")
            if f in families
        ),
        "",
    )
    app.setFont(QFont(family, 13))
    app.setStyleSheet(STYLE)

    win = MainWindow(
        device, a.model, a.lang, a.out, selftest=a.selftest,
        whisper_device=a.whisper_device, whisper_compute=a.whisper_compute,
        whisper_threads=a.whisper_threads, whisper_beam=a.whisper_beam,
    )
    win.show()

    if a.selftest:
        win.stt.ready.connect(win._selftest_ready)
        QTimer.singleShot(60000, win.close)

    code = app.exec()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
