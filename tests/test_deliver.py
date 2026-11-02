"""合规交付测试。"""
from __future__ import annotations

import json

import pytest

from filmforge.deliver import build_attribution, make_delivery
from filmforge.registry import SourceRegistry


def _make_project(tmp_path, sources_used=None) -> tuple:
    project = tmp_path / "proj"
    (project / "films").mkdir(parents=True)
    (project / "films" / "film.html").write_text("<html></html>", encoding="utf-8")
    (project / "final.mp4").write_bytes(b"fake-video")
    storyboard = {
        "project": "测试",
        "duration": 10,
        "aspect": "16:9",
        "sources_used": sources_used or ["openfilm"],
        "scenes": [],
    }
    (project / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False), encoding="utf-8"
    )
    return project, tmp_path / "dist"


def test_attribution_contains_license_requirements() -> None:
    text = build_attribution(["lemo-opuscar", "openfilm"], SourceRegistry())
    assert "CC BY 4.0" in text
    assert "署名" in text
    assert "openfilm/openfilm" in text


def test_attribution_marks_noncommercial() -> None:
    text = build_attribution(["onetake"], SourceRegistry())
    assert "禁止商用" in text


def test_delivery_package(tmp_path) -> None:
    project, out = _make_project(tmp_path)
    make_delivery(project, out)
    assert (out / "成片.mp4").exists()
    assert (out / "films" / "film.html").exists()
    assert (out / "storyboard.json").exists()
    report = (out / "attribution.md").read_text(encoding="utf-8")
    assert "openfilm" in report


def test_delivery_rejects_noncommercial(tmp_path) -> None:
    project, out = _make_project(tmp_path, sources_used=["onetake"])
    with pytest.raises(ValueError, match="禁止商用"):
        make_delivery(project, out)


def test_delivery_unknown_source(tmp_path) -> None:
    project, out = _make_project(tmp_path, sources_used=["nope"])
    with pytest.raises(KeyError, match="nope"):
        make_delivery(project, out)


def test_delivery_missing_storyboard(tmp_path) -> None:
    with pytest.raises(ValueError, match="storyboard.json"):
        make_delivery(tmp_path, tmp_path / "dist")
