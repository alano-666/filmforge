"""brief 与提示词组装测试。"""
from __future__ import annotations

import json

import pytest

from filmforge.brief import (
    BRIEF_TEMPLATE,
    STORYBOARD_TEMPLATE,
    Scene,
    Storyboard,
    build_prompt,
    build_voice_lines,
)
from filmforge.registry import load_bundled_styles


def _storyboard(**overrides) -> dict:
    data = dict(STORYBOARD_TEMPLATE)
    data.update(
        {
            "project": "测试产品",
            "duration": 10,
            "aspect": "16:9",
            "sources_used": ["lemo-opuscar"],
            "scenes": [
                {
                    "id": "s1",
                    "start": 0,
                    "end": 3,
                    "text": "logo 揭示",
                    "voiceover": "欢迎来到测试产品",
                    "style": "enterprise-blue",
                    "motion": "圆环展开",
                },
                {
                    "id": "s2",
                    "start": 3,
                    "end": 10,
                    "text": "数据展示",
                    "voiceover": "",
                    "style": "enterprise-blue",
                    "motion": "数字滚动",
                },
            ],
        }
    )
    data.update(overrides)
    return data


def test_brief_template_has_sections() -> None:
    for key in ("客户与产品", "成片要求", "调性与风格", "必含信息", "交付物"):
        assert key in BRIEF_TEMPLATE


def test_scene_validation() -> None:
    with pytest.raises(ValueError, match="缺少字段"):
        Scene.from_dict({"id": "s"})
    with pytest.raises(ValueError, match="时间区间非法"):
        Scene.from_dict(
            {"id": "s", "start": 5, "end": 3, "text": "", "voiceover": "", "style": "", "motion": ""}
        )


def test_storyboard_round_trip(tmp_path) -> None:
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(_storyboard(), ensure_ascii=False), encoding="utf-8")
    sb = Storyboard.load(path)
    assert sb.project == "测试产品"
    assert len(sb.scenes) == 2
    assert sb.sources_used == ["lemo-opuscar"]
    assert sb.to_dict()["scenes"][0]["id"] == "s1"


def test_storyboard_duration_mismatch(tmp_path) -> None:
    path = tmp_path / "storyboard.json"
    path.write_text(
        json.dumps(_storyboard(duration=99), ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="不一致"):
        Storyboard.load(path)


def test_storyboard_missing_key(tmp_path) -> None:
    path = tmp_path / "storyboard.json"
    path.write_text('{"project": "x"}', encoding="utf-8")
    with pytest.raises(ValueError, match="缺少字段"):
        Storyboard.load(path)


def test_build_prompt_contains_all_sections(tmp_path) -> None:
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(_storyboard(), ensure_ascii=False), encoding="utf-8")
    sb = Storyboard.load(path)
    styles = [load_bundled_styles()["enterprise-blue"]]
    prompt = build_prompt("客户是一家奶茶店", sb, styles)
    assert "客户是一家奶茶店" in prompt
    assert "s1" in prompt or "logo 揭示" in prompt
    assert "深空蓝" in prompt
    assert "frame(t)" in prompt
    assert "?t=" in prompt
    assert "film.html" in prompt


def test_voice_lines() -> None:
    sb = Storyboard(
        project="x",
        duration=10,
        aspect="16:9",
        scenes=[
            Scene(id="a", start=0, end=5, text="", voiceover="第一句"),
            Scene(id="b", start=5, end=10, text="", voiceover=""),
            Scene(id="c", start=5, end=10, text="", voiceover="第二句"),
        ],
    )
    assert build_voice_lines(sb) == ["第一句", "第二句"]
