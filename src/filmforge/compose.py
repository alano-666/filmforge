"""配音与合成：edge-tts 生成配音，ffmpeg 拼接成片并混音。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class ComposeError(RuntimeError):
    pass


def build_tts_command(text: str, out_path: Path, *, voice: str = DEFAULT_VOICE) -> list[str]:
    return ["edge-tts", "--voice", voice, "--text", text, "--write-media", str(out_path)]


def tts(text: str, out_path: Path, *, voice: str = DEFAULT_VOICE) -> Path:
    if not shutil.which("edge-tts"):
        raise ComposeError("未找到 edge-tts。安装: pip install edge-tts")
    proc = subprocess.run(
        build_tts_command(text, out_path, voice=voice),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise ComposeError(f"edge-tts 失败: {proc.stderr.strip()[:300]}")
    return out_path


def build_concat_list(clips: list[Path]) -> str:
    return "".join(f"file '{clip.resolve()}'\n" for clip in clips)


def build_concat_command(
    list_path: Path,
    out_path: Path,
    *,
    audio: Path | None = None,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """v0.1 约束：所有片段需同一分辨率/编码（本管线自己渲染的片段满足）。"""
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path)]
    if audio is not None:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a"]
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-shortest"]
    else:
        cmd += ["-c:v", "libx264", "-an"]
    cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    return cmd


def compose(clips: list[Path], out_path: Path, *, audio: Path | None = None) -> Path:
    if not clips:
        raise ComposeError("片段列表为空")
    if not shutil.which("ffmpeg"):
        raise ComposeError("未找到 ffmpeg。macOS: brew install ffmpeg")
    for clip in clips:
        if not clip.exists():
            raise ComposeError(f"片段不存在: {clip}")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", prefix="filmforge-concat-", delete=False
    ) as f:
        f.write(build_concat_list(clips))
        list_path = Path(f.name)

    try:
        proc = subprocess.run(
            build_concat_command(list_path, out_path, audio=audio),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise ComposeError(f"ffmpeg 拼接失败: {proc.stderr.strip()[:300]}")
    finally:
        list_path.unlink(missing_ok=True)
    return out_path
