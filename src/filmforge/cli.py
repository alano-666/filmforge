"""命令行入口。

工作流：
  filmforge new <项目名>                    初始化项目（brief/storyboard/合规清单）
  filmforge sources                         查看可整合的开源库与许可
  filmforge style list                      列出可用风格
  filmforge brief prompt --style <s>        组装给 Claude Code 的生成提示词
  filmforge render <film.html> -o out.mp4   逐帧渲染成 MP4
  filmforge voice <文本> -o vo.mp3          生成配音
  filmforge compose <片段...> -o final.mp4  拼接成片（可混音）
  filmforge deliver <项目> -o dist/         打包交付（含署名报告）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .brief import (
    BRIEF_TEMPLATE,
    STORYBOARD_TEMPLATE,
    Storyboard,
    build_prompt,
    build_voice_lines,
)
from .compose import ComposeError, compose, tts
from .deliver import make_delivery
from .registry import (
    SourceRegistry,
    load_bundled_styles,
    load_project_styles,
)
from .render import RenderError, render_film

DEFAULT_SIZE = (1920, 1080)


def _resolve_styles(args) -> list:
    styles = load_bundled_styles()
    cwd_project = Path.cwd() / "storyboard.json"
    if cwd_project.exists():
        styles.update(load_project_styles(Path.cwd()))
    if getattr(args, "style", ""):
        requested = [s.strip() for s in args.style.split(",") if s.strip()]
        missing = [s for s in requested if s not in styles]
        if missing:
            raise KeyError(f"未找到风格: {', '.join(missing)}，可用: {', '.join(styles)}")
        return [styles[s] for s in requested]
    return list(styles.values())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filmforge",
        description="AI 宣传片制作管线：brief → 分镜 → 生成 → 渲染 → 配音 → 合规交付",
    )
    parser.add_argument("--version", action="version", version=f"filmforge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="初始化项目目录")
    p_new.add_argument("name", help="项目名（目录名）")

    sub.add_parser("sources", help="查看可整合的开源库与许可")

    p_style = sub.add_parser("style", help="风格管理")
    p_style.add_argument("action", choices=["list"])

    p_brief = sub.add_parser("brief", help="brief 与提示词")
    p_brief.add_argument("action", choices=["prompt", "voice"])
    p_brief.add_argument("--style", default="", help="风格 id，逗号分隔（默认全部内置风格）")
    p_brief.add_argument("--out", help="提示词输出到文件")

    p_render = sub.add_parser("render", help="逐帧渲染 film.html 为 MP4")
    p_render.add_argument("html", help="film.html 路径")
    p_render.add_argument("-o", "--out", required=True)
    p_render.add_argument("--duration", type=float, required=True, help="时长（秒）")
    p_render.add_argument("--fps", type=int, default=30)
    p_render.add_argument("--width", type=int, default=DEFAULT_SIZE[0])
    p_render.add_argument("--height", type=int, default=DEFAULT_SIZE[1])

    p_voice = sub.add_parser("voice", help="edge-tts 配音")
    p_voice.add_argument("text")
    p_voice.add_argument("-o", "--out", required=True)
    p_voice.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")

    p_compose = sub.add_parser("compose", help="拼接片段成片")
    p_compose.add_argument("clips", nargs="+", help="片段文件（渲染产物）")
    p_compose.add_argument("-o", "--out", required=True)
    p_compose.add_argument("--audio", help="配音文件（mp3/wav）")

    p_deliver = sub.add_parser("deliver", help="打包交付（含署名报告）")
    p_deliver.add_argument("project", help="项目目录")
    p_deliver.add_argument("-o", "--out", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "new":
            project_dir = Path(args.name)
            if project_dir.exists():
                raise ValueError(f"目录已存在: {project_dir}")
            (project_dir / "films").mkdir(parents=True)
            (project_dir / "brief.md").write_text(BRIEF_TEMPLATE, encoding="utf-8")
            (project_dir / "storyboard.json").write_text(
                json.dumps(STORYBOARD_TEMPLATE, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"项目已创建: {project_dir}/")
            print("下一步: 填写 brief.md → 填 storyboard.json → filmforge brief prompt")

        elif args.command == "sources":
            registry = SourceRegistry()
            for s in registry.sources:
                mark = "✓ 可商用" if s.commercial else "✗ 禁止商用"
                print(f"{mark}  {s.repo}  [{s.type}]  {s.license}")

        elif args.command == "style":
            styles = load_bundled_styles()
            styles.update(load_project_styles(Path.cwd()))
            if not styles:
                print("（无可用风格）")
            for style_id, pack in styles.items():
                print(
                    f"{style_id:<20} {pack.name}  "
                    f"{pack.aspect} {pack.duration:.0f}s  {pack.license}  "
                    f"{', '.join(pack.tags)}"
                )

        elif args.command == "brief":
            storyboard = Storyboard.load(Path("storyboard.json"))
            if args.action == "prompt":
                brief = Path("brief.md").read_text(encoding="utf-8")
                styles = _resolve_styles(args)
                prompt = build_prompt(brief, storyboard, styles)
                if args.out:
                    Path(args.out).write_text(prompt, encoding="utf-8")
                    print(f"提示词已写入 {args.out}")
                else:
                    print(prompt)
            elif args.action == "voice":
                lines = build_voice_lines(storyboard)
                if not lines:
                    print("（分镜中没有配音文本）")
                for i, line in enumerate(lines):
                    print(f"[{i}] {line}")

        elif args.command == "render":
            result = render_film(
                Path(args.html),
                Path(args.out),
                duration=args.duration,
                fps=args.fps,
                size=(args.width, args.height),
            )
            print(f"渲染完成: {result.out_path}（{result.frames} 帧 @ {result.fps}fps）")

        elif args.command == "voice":
            out = tts(args.text, Path(args.out), voice=args.voice)
            print(f"配音完成: {out}")

        elif args.command == "compose":
            out = compose(
                [Path(c) for c in args.clips], Path(args.out), audio=Path(args.audio) if args.audio else None
            )
            print(f"成片完成: {out}")

        elif args.command == "deliver":
            out = make_delivery(Path(args.project), Path(args.out))
            print(f"交付包已生成: {out}/")
            print("包含: 成片.mp4 / films 源文件 / storyboard.json / attribution.md")

    except (ValueError, KeyError, OSError, RenderError, ComposeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
