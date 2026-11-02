"""开源库注册表与风格包加载。

- sources.json 记录可整合的开源库：许可、商用结论、署名要求。
- StylePack：内置风格（styles/*/）与项目自定义风格，schema 校验。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

REQUIRED_FIELDS = {"name", "version", "license", "tags", "aspect", "duration"}


@dataclass(frozen=True)
class Source:
    id: str
    repo: str
    type: str
    license: str
    commercial: bool
    usage: str
    attribution: str


@dataclass(frozen=True)
class StylePack:
    id: str
    name: str
    version: str
    license: str
    tags: list[str]
    aspect: str
    duration: float
    prompt: str
    example: Path


class SourceRegistry:
    def __init__(self, data_path: Path | None = None) -> None:
        if data_path is None:
            data_path = Path(str(files("filmforge").joinpath("data", "sources.json")))
        raw = json.loads(data_path.read_text(encoding="utf-8"))
        self._sources = {item["id"]: Source(**item) for item in raw}

    @property
    def sources(self) -> list[Source]:
        return list(self._sources.values())

    def get(self, source_id: str) -> Source:
        if source_id not in self._sources:
            raise KeyError(f"未知开源库: {source_id}，可用: {', '.join(self._sources)}")
        return self._sources[source_id]

    def commercial_sources(self) -> list[Source]:
        return [s for s in self._sources.values() if s.commercial]


def load_style_pack(style_dir: Path) -> StylePack:
    meta_path = style_dir / "style.json"
    prompt_path = style_dir / "prompt.md"
    example_path = style_dir / "example.html"
    if not meta_path.exists():
        raise ValueError(f"风格目录缺少 style.json: {style_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    missing = REQUIRED_FIELDS - set(meta)
    if missing:
        raise ValueError(f"{style_dir.name} 的 style.json 缺少字段: {sorted(missing)}")
    if not prompt_path.exists():
        raise ValueError(f"风格目录缺少 prompt.md: {style_dir}")
    if not example_path.exists():
        raise ValueError(f"风格目录缺少 example.html: {style_dir}")
    return StylePack(
        id=style_dir.name,
        name=meta["name"],
        version=meta["version"],
        license=meta["license"],
        tags=list(meta["tags"]),
        aspect=meta["aspect"],
        duration=float(meta["duration"]),
        prompt=prompt_path.read_text(encoding="utf-8"),
        example=example_path,
    )


def load_bundled_styles() -> dict[str, StylePack]:
    base = Path(str(files("filmforge").joinpath("styles")))
    return {p.id: p for p in (load_style_pack(d) for d in sorted(base.iterdir()) if d.is_dir())}


def load_project_styles(project_dir: Path) -> dict[str, StylePack]:
    styles_dir = project_dir / "styles"
    if not styles_dir.is_dir():
        return {}
    return {
        p.id: p
        for p in (load_style_pack(d) for d in sorted(styles_dir.iterdir()) if d.is_dir())
    }
