"""开源库注册表与风格包测试。"""
from __future__ import annotations

import pytest

from filmforge.registry import (
    SourceRegistry,
    load_bundled_styles,
    load_style_pack,
)


def test_sources_registry_loads() -> None:
    registry = SourceRegistry()
    ids = [s.id for s in registry.sources]
    assert {"lemo-opuscar", "mg-styles-15", "huashu-motion", "openfilm", "onetake"} <= set(ids)


def test_commercial_flags() -> None:
    registry = SourceRegistry()
    assert registry.get("onetake").commercial is False
    assert all(
        s.commercial for s in registry.commercial_sources()
    ), "commercial_sources 不应包含禁商用库"


def test_get_unknown_raises() -> None:
    with pytest.raises(KeyError, match="nope"):
        SourceRegistry().get("nope")


def test_bundled_style_pack_valid() -> None:
    styles = load_bundled_styles()
    assert "enterprise-blue" in styles
    pack = styles["enterprise-blue"]
    assert pack.aspect == "16:9"
    assert pack.duration > 0
    assert pack.prompt.strip()
    assert pack.example.exists()
    content = pack.example.read_text(encoding="utf-8")
    assert "frame(t)" in content
    assert 'params.get("t")' in content


def test_style_pack_missing_meta(tmp_path) -> None:
    d = tmp_path / "broken"
    d.mkdir()
    with pytest.raises(ValueError, match="style.json"):
        load_style_pack(d)


def test_style_pack_incomplete_fields(tmp_path) -> None:
    d = tmp_path / "incomplete"
    d.mkdir()
    (d / "style.json").write_text('{"name": "x"}', encoding="utf-8")
    (d / "prompt.md").write_text("p", encoding="utf-8")
    (d / "example.html").write_text("e", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少字段"):
        load_style_pack(d)


def test_style_pack_missing_prompt(tmp_path) -> None:
    d = tmp_path / "noprompt"
    d.mkdir()
    (d / "style.json").write_text(
        '{"name":"x","version":"1","license":"MIT","tags":[],"aspect":"16:9","duration":10}',
        encoding="utf-8",
    )
    (d / "example.html").write_text("e", encoding="utf-8")
    with pytest.raises(ValueError, match="prompt.md"):
        load_style_pack(d)
