"""渲染：headless Chrome 逐帧截图 + ffmpeg 合成 MP4。

film.html 需支持 ?t=<秒> 参数（见 brief.py 输出规范）。
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

# headless Chrome 的窗口高度与页面视口高度的差值（macOS headless=new 实测 87px）。
# 渲染时把窗口加高 VIEWPORT_OFFSET，使视口正好等于目标尺寸，再用 ffmpeg 裁掉多余区域；
# 在偏移为 0 的环境（如 Linux headless）下同样成立（缩放按视口计算，裁切为安全裁剪）。
VIEWPORT_OFFSET = 87


class RenderError(RuntimeError):
    pass


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return shutil.which("google-chrome") or shutil.which("chromium")


def build_frame_commands(
    html_path: Path,
    frames_dir: Path,
    *,
    duration: float,
    fps: int,
    size: tuple[int, int],
    chrome: str,
    window_offset: int = VIEWPORT_OFFSET,
) -> list[list[str]]:
    """纯函数：生成逐帧截图命令列表（可单测）。窗口高度 = 目标高度 + 视口偏移。"""
    width, height = size
    commands = []
    frame_count = int(round(duration * fps))
    for i in range(frame_count):
        t = i / fps
        shot = frames_dir / f"frame_{i:05d}.png"
        commands.append(
            [
                chrome,
                "--headless=new",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={width},{height + window_offset}",
                f"--virtual-time-budget={(t * 1000 + 500):.0f}",
                f"--screenshot={shot}",
                f"file://{html_path}?t={t}",
            ]
        )
    return commands


def build_mp4_command(
    frames_dir: Path,
    out_path: Path,
    *,
    fps: int,
    ffmpeg: str = "ffmpeg",
    crop_bottom: int = VIEWPORT_OFFSET,
) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%05d.png"),
        "-vf",
        f"crop=iw:ih-{crop_bottom}:0:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]


@dataclass
class RenderResult:
    out_path: Path
    frames: int
    fps: int


def render_film(
    html_path: Path,
    out_path: Path,
    *,
    duration: float,
    fps: int = 30,
    size: tuple[int, int] = (1920, 1080),
    work_dir: Path | None = None,
) -> RenderResult:
    html_path = html_path.resolve()
    if not html_path.exists():
        raise RenderError(f"film.html 不存在: {html_path}")
    out_path = out_path.resolve()
    chrome = find_chrome()
    if not chrome:
        raise RenderError("未找到 Chrome/Chromium，请安装后重试")
    if not shutil.which("ffmpeg"):
        raise RenderError("未找到 ffmpeg。macOS: brew install ffmpeg")

    frames_dir = work_dir or out_path.parent / f".frames-{out_path.stem}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    commands = build_frame_commands(
        html_path, frames_dir, duration=duration, fps=fps, size=size, chrome=chrome
    )
    for i, cmd in enumerate(commands):
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RenderError(f"第 {i} 帧截图失败: {proc.stderr.strip()[:300]}")

    mp4_cmd = build_mp4_command(frames_dir, out_path, fps=fps)
    proc = subprocess.run(mp4_cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RenderError(f"ffmpeg 合成失败: {proc.stderr.strip()[:300]}")

    return RenderResult(out_path=out_path, frames=len(commands), fps=fps)
