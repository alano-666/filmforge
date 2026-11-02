"""合规交付：打包成片 + 源文件 + 第三方署名报告。

每个交付包附 attribution.md，列出用到的开源库及其许可要求——
这是正规交付与「野路子视频」的核心差异，也是服务卖点。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .registry import SourceRegistry


def build_attribution(source_ids: list[str], registry: SourceRegistry) -> str:
    lines = [
        "# 第三方开源组件署名报告",
        "",
        f"本交付物使用以下开源项目（{len(source_ids)} 个）：",
        "",
    ]
    for source_id in source_ids:
        source = registry.get(source_id)
        lines += [
            f"## {source.repo}",
            f"- 用途：{source.usage}",
            f"- 许可：{source.license}",
            f"- 商用：{'允许' if source.commercial else '禁止'}",
            f"- 署名要求：{source.attribution}",
            "",
        ]
    return "\n".join(lines)


def make_delivery(
    project_dir: Path,
    out_dir: Path,
    *,
    registry: SourceRegistry | None = None,
) -> Path:
    storyboard_path = project_dir / "storyboard.json"
    if not storyboard_path.exists():
        raise ValueError(f"缺少 storyboard.json: {project_dir}")

    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    registry = registry or SourceRegistry()

    noncommercial = [s for s in storyboard.get("sources_used", []) if not registry.get(s).commercial]
    if noncommercial:
        raise ValueError(
            f"分镜使用了禁止商用的开源库: {', '.join(noncommercial)}，请替换后重新生成"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    final_video = project_dir / "final.mp4"
    if final_video.exists():
        shutil.copy2(final_video, out_dir / "成片.mp4")

    films_dir = project_dir / "films"
    if films_dir.is_dir():
        shutil.copytree(films_dir, out_dir / "films", dirs_exist_ok=True)

    shutil.copy2(storyboard_path, out_dir / "storyboard.json")

    attribution = build_attribution(
        storyboard.get("sources_used", []), registry
    )
    (out_dir / "attribution.md").write_text(attribution, encoding="utf-8")

    return out_dir
