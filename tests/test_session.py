"""Testes para a classe Session (gravacao de transcricao)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speechscribe.session import Session


def test_session_saves_txt_and_json_by_default(tmp_path: Path):
    """Por default, grava .txt, .wav e .json com segmentos."""
    s = Session(tmp_path, "tiny", "pt", save_txt=True, save_segments=True)
    s.open()
    s.add("olá mundo", 0.0, 1.0)
    s.add("testando", 1.5, 2.5)
    paths = s.close()

    assert Path(paths["txt"]).exists()
    assert Path(paths["wav"]).exists()
    assert Path(paths["json"]).exists()

    data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert len(data["segmentos"]) == 2
    assert data["segmentos"][0]["texto"] == "olá mundo"


def test_session_no_txt_when_save_txt_false(tmp_path: Path):
    """Quando save_txt=False, nao grava arquivo de texto."""
    s = Session(tmp_path, "tiny", "pt", save_txt=False, save_segments=True)
    s.open()
    s.add("qualquer coisa", 0.0, 1.0)
    paths = s.close()

    assert not Path(paths["txt"]).exists()
    assert Path(paths["wav"]).exists()
    assert Path(paths["json"]).exists()


def test_session_no_json_segments_when_save_segments_false(tmp_path: Path):
    """Quando save_segments=False, grava .json sem a chave segmentos."""
    s = Session(tmp_path, "tiny", "pt", save_txt=True, save_segments=False)
    s.open()
    s.add("qualquer coisa", 0.0, 1.0)
    paths = s.close()

    assert Path(paths["txt"]).exists()
    assert Path(paths["wav"]).exists()
    assert Path(paths["json"]).exists()

    data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert "segmentos" not in data


def test_session_neither_txt_nor_segments(tmp_path: Path):
    """Quando ambos sao False, so grava .wav."""
    s = Session(tmp_path, "tiny", "pt", save_txt=False, save_segments=False)
    s.open()
    s.add("qualquer coisa", 0.0, 1.0)
    paths = s.close()

    assert not Path(paths["txt"]).exists()
    assert Path(paths["wav"]).exists()
    assert Path(paths["json"]).exists()

    data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert "segmentos" not in data


def test_session_words_count(tmp_path: Path):
    """A contagem de palavras e incrementada corretamente."""
    s = Session(tmp_path, "tiny", "pt")
    s.open()
    s.add("um dois tres", 0.0, 1.0)
    s.add("quatro cinco", 1.0, 2.0)
    assert s.words == 5
