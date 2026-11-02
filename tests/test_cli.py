"""CLI 端到端测试（不触发真实 Chrome/ffmpeg/网络）。"""
from __future__ import annotations

import json
import os

from filmforge.cli import main


def _init_project(tmp_path) -> None:
    os.chdir(tmp_path)
    assert main(["new", "demo"]) == 0
    project = tmp_path / "demo"
    storyboard = {
        "project": "演示产品",
        "duration": 10,
        "aspect": "16:9",
        "sources_used": ["openfilm", "lemo-opuscar"],
        "scenes": [
            {
                "id": "s1",
                "start": 0,
                "end": 10,
                "text": "开场",
                "voiceover": "你好",
                "style": "enterprise-blue",
                "motion": "圆环展开",
            }
        ],
    }
    (project / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False), encoding="utf-8"
    )
    (project / "brief.md").write_text("客户是一家奶茶店", encoding="utf-8")
    os.chdir(project)


def test_new_creates_skeleton(tmp_path, capsys) -> None:
    os.chdir(tmp_path)
    assert main(["new", "demo"]) == 0
    assert (tmp_path / "demo" / "brief.md").exists()
    assert (tmp_path / "demo" / "storyboard.json").exists()
    assert (tmp_path / "demo" / "films").is_dir()
    out = capsys.readouterr().out
    assert "项目已创建" in out


def test_new_existing_dir_fails(tmp_path, capsys) -> None:
    os.chdir(tmp_path)
    main(["new", "demo"])
    assert main(["new", "demo"]) == 1
    assert "已存在" in capsys.readouterr().err


def test_sources_lists_licenses(tmp_path, capsys) -> None:
    os.chdir(tmp_path)
    assert main(["sources"]) == 0
    out = capsys.readouterr().out
    assert "可商用" in out
    assert "onetake" in out and "禁止商用" in out


def test_style_list(tmp_path, capsys) -> None:
    os.chdir(tmp_path)
    assert main(["style", "list"]) == 0
    out = capsys.readouterr().out
    assert "enterprise-blue" in out
    assert "深空蓝" in out


def test_brief_prompt(tmp_path, capsys) -> None:
    _init_project(tmp_path)
    assert main(["brief", "prompt", "--style", "enterprise-blue"]) == 0
    out = capsys.readouterr().out
    assert "奶茶店" in out
    assert "frame(t)" in out
    assert "film.html" in out


def test_brief_prompt_unknown_style_fails(tmp_path, capsys) -> None:
    _init_project(tmp_path)
    assert main(["brief", "prompt", "--style", "nope"]) == 1
    assert "未找到风格" in capsys.readouterr().err


def test_brief_voice(tmp_path, capsys) -> None:
    _init_project(tmp_path)
    assert main(["brief", "voice"]) == 0
    assert "你好" in capsys.readouterr().out


def test_deliver_full_flow(tmp_path, capsys) -> None:
    _init_project(tmp_path)
    project = tmp_path / "demo"
    (project / "final.mp4").write_bytes(b"video")
    assert main(["deliver", ".", "-o", "dist"]) == 0
    dist = project / "dist"
    assert (dist / "成片.mp4").exists()
    report = (dist / "attribution.md").read_text(encoding="utf-8")
    assert "lemo-opuscar" in report
    assert "CC BY 4.0" in report
    assert "交付包已生成" in capsys.readouterr().out


def test_deliver_rejects_onetake(tmp_path, capsys) -> None:
    _init_project(tmp_path)
    sb = json.loads((tmp_path / "demo" / "storyboard.json").read_text(encoding="utf-8"))
    sb["sources_used"] = ["onetake"]
    (tmp_path / "demo" / "storyboard.json").write_text(
        json.dumps(sb, ensure_ascii=False), encoding="utf-8"
    )
    assert main(["deliver", ".", "-o", "dist"]) == 1
    assert "禁止商用" in capsys.readouterr().err


def test_version(capsys) -> None:
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "filmforge" in capsys.readouterr().out
