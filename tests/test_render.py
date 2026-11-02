"""渲染与合成命令构造测试（纯函数，不实际调用 Chrome/ffmpeg）。"""
from __future__ import annotations

from pathlib import Path

from filmforge.compose import (
    build_concat_command,
    build_concat_list,
    build_tts_command,
)
from filmforge.render import build_frame_commands, build_mp4_command


def test_frame_commands_count_and_timing() -> None:
    cmds = build_frame_commands(
        Path("/tmp/film.html"),
        Path("/tmp/frames"),
        duration=2,
        fps=5,
        size=(640, 360),
        chrome="/fake/chrome",
        window_offset=87,
    )
    assert len(cmds) == 10
    for i, cmd in enumerate(cmds):
        t = i / 5
        assert "--screenshot=/tmp/frames/frame_0000%d.png" % i in " ".join(cmd)
        assert f"film.html?t={t}" in cmd[-1]


def test_frame_command_flags() -> None:
    cmds = build_frame_commands(
        Path("f.html"), Path("fr"), duration=0.2, fps=5, size=(1920, 1080), chrome="c"
    )
    cmd = cmds[0]
    assert "--headless=new" in cmd
    assert "--window-size=1920,1167" in cmd  # 1080 + 视口偏移 87
    assert "--force-device-scale-factor=1" in cmd


def test_frame_command_zero_offset() -> None:
    cmds = build_frame_commands(
        Path("f.html"), Path("fr"), duration=0.2, fps=5, size=(640, 360), chrome="c",
        window_offset=0,
    )
    assert "--window-size=640,360" in cmds[0]


def test_mp4_command() -> None:
    cmd = build_mp4_command(Path("/tmp/frames"), Path("/tmp/out.mp4"), fps=30)
    assert cmd[0] == "ffmpeg"
    assert "-framerate" in cmd and "30" in cmd
    assert any("frame_%05d.png" in c for c in cmd)
    assert cmd[-1] == "/tmp/out.mp4"
    assert "libx264" in cmd
    assert "crop=iw:ih-87:0:0" in cmd


def test_tts_command() -> None:
    cmd = build_tts_command("你好", Path("/tmp/vo.mp3"))
    assert cmd[0] == "edge-tts"
    assert cmd[2] == "zh-CN-XiaoxiaoNeural"
    assert cmd[4] == "你好"
    assert cmd[-1] == "/tmp/vo.mp3"


def test_concat_list_content() -> None:
    content = build_concat_list([Path("/a/1.mp4"), Path("/a/2.mp4")])
    assert content == "file '/a/1.mp4'\nfile '/a/2.mp4'\n"


def test_concat_command_no_audio() -> None:
    cmd = build_concat_command(Path("/tmp/list.txt"), Path("/out.mp4"))
    assert cmd[0] == "ffmpeg"
    assert "-f" in cmd and "concat" in cmd
    assert "/tmp/list.txt" in cmd
    assert "-an" in cmd
    assert cmd[-1] == "/out.mp4"


def test_concat_command_with_audio() -> None:
    cmd = build_concat_command(
        Path("/tmp/list.txt"), Path("/out.mp4"), audio=Path("/a/vo.mp3")
    )
    assert "-i" in cmd and "/a/vo.mp3" in cmd
    assert "-map" in cmd and "0:v" in cmd and "1:a" in cmd
    assert "aac" in cmd
    assert "-shortest" in cmd
