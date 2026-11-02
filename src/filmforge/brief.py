"""brief、分镜 schema 与「给 Claude Code 的提示词」组装。

流程：客户需求 → brief.md → storyboard.json → build_prompt() 组装提示词
→ Claude Code 生成 film.html（openfilm 格式）→ 渲染。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

BRIEF_TEMPLATE = """# 项目简报

## 客户与产品
公司名称：
产品/服务：
一句话卖点：

## 成片要求
时长（秒）：
画面比例：
目标受众：
投放场景（发布会/官网/展会/投流）：

## 调性与风格
关键词（如 科技/温暖/高端）：
参考影片链接：
品牌色（主色/辅色）：

## 必含信息
1.
2.

## 交付物
成片格式（MP4 分辨率）：
配音需求（男/女声、语速）：
"""

STORYBOARD_TEMPLATE = {
    "project": "",
    "duration": 30,
    "aspect": "16:9",
    "sources_used": [],
    "scenes": [],
}

SCENE_KEYS = {"id", "start", "end", "text", "voiceover", "style", "motion"}


@dataclass
class Scene:
    id: str
    start: float
    end: float
    text: str
    voiceover: str = ""
    style: str = ""
    motion: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "voiceover": self.voiceover,
            "style": self.style,
            "motion": self.motion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        missing = SCENE_KEYS - set(data)
        if missing:
            raise ValueError(f"分镜场景缺少字段: {sorted(missing)}")
        if not (0 <= data["start"] < data["end"]):
            raise ValueError(f"场景 {data.get('id')} 时间区间非法: {data['start']}-{data['end']}")
        return cls(**data)


@dataclass
class Storyboard:
    project: str
    duration: float
    aspect: str
    scenes: list[Scene]
    sources_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "duration": self.duration,
            "aspect": self.aspect,
            "sources_used": list(self.sources_used),
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def load(cls, path: Path) -> "Storyboard":
        raw = json.loads(path.read_text(encoding="utf-8"))
        for key in ("project", "duration", "aspect", "scenes"):
            if key not in raw:
                raise ValueError(f"storyboard.json 缺少字段: {key}")
        scenes = [Scene.from_dict(s) for s in raw["scenes"]]
        total = sum(s.end - s.start for s in scenes)
        if abs(total - raw["duration"]) > 0.5:
            raise ValueError(
                f"分镜总时长 {total}s 与成片时长 {raw['duration']}s 不一致"
            )
        return cls(
            project=raw["project"],
            duration=raw["duration"],
            aspect=raw["aspect"],
            scenes=scenes,
            sources_used=list(raw.get("sources_used", [])),
        )


def build_prompt(brief: str, storyboard: Storyboard, style_packs: list) -> str:
    """组装给 Claude Code 的完整生成提示词（确定性文本，便于测试与复用）。"""
    style_section = "\n\n".join(
        f"### 风格「{p.name}」\n{p.prompt}" for p in style_packs
    )
    scenes_section = "\n".join(
        f"- [{s.start:>5.1f}s - {s.end:>5.1f}s] {s.text}"
        + (f" ｜ 配音: {s.voiceover}" if s.voiceover else "")
        + (f" ｜ 动效: {s.motion}" if s.motion else "")
        for s in storyboard.scenes
    )
    return f"""# 任务：为以下宣传片生成 film.html（openfilm 格式）

## 项目简报
{brief}

## 分镜
{scenes_section}

## 风格要求
{style_section}

## 输出规范（必须遵守）
1. 单一 HTML 文件，所有动画由 frame(t) 函数驱动（t 为秒数，浮点）；
2. 页面必须支持 URL 参数 ?t=<秒>：加载时直接渲染该时刻的静止画面（用于逐帧渲染）；
3. 无 ?t 参数时用 requestAnimationFrame 正常播放；
4. 分辨率 {storyboard.aspect}（16:9 即 1920x1080），全屏适配；
5. 不依赖网络：字体用系统字体栈，图片素材必须内联（SVG/Canvas/程序化生成）；
6. 每个分镜是一段连续动效，注意画面转场（淡入淡出/位移/缩放，禁止硬切）；
7. 输出文件名：film.html。

完成后用 filmforge render 渲染检查，再交付审片。
"""


def build_voice_lines(storyboard: Storyboard) -> list[str]:
    return [s.voiceover for s in storyboard.scenes if s.voiceover]
