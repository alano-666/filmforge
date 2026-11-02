# 🎬 filmforge · AI 宣传片制作管线

> **用代码做宣传片。** 整合开源风格库与渲染工具：brief → 分镜 → Claude Code 生成 → 逐帧渲染 → 配音配乐 → 合规交付。
> 单人交付，3 天出片，价格是传统制作的三分之一。

EN: An open pipeline for AI-generated commercial films — brief → storyboard → agent-generated `film.html` → frame-accurate render → voiceover → licensed delivery.

## 为什么是现在

- **开源风格库爆发**：lemo-opuscar（66 风格）、mg-styles-15（15 风格）、huashu-motion（整片工作流）都是 2026 年 9-10 月的万星项目，代码渲染动效已经达到商业级
- **但没有人做「交付层」**：这些项目解决「怎么生成」，不解决「怎么接单、怎么合规交付、怎么保证成片质量」
- filmforge 就是这个胶水层：把开源能力串成一条可收费的服务管线

## 整合的开源项目

| 项目 | 星数 | 许可 | 在本管线中的角色 |
|---|---|---|---|
| [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | 10.8k | MIT / CC BY 4.0 | 66 种影片风格库 |
| [openfilm/openfilm](https://github.com/openfilm/openfilm) | 4.2k | MIT | film.html 成片格式 + 审片编辑器 |
| [Vincentwei1021/mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15) | 2.9k | MIT | 15 种 MG 风格参考（提示词+源码） |
| [alchaincyf/huashu-motion](https://github.com/alchaincyf/huashu-motion) | 2.0k | MIT | 整片工作流（需求→三方向→成片+配乐） |
| ~~feitangyuan/onetake~~ | 3.6k | **PolyForm Noncommercial** | ❌ 禁止商用，仅供内部学习（合规红线） |

**合规是卖点**：每个交付包自动生成 `attribution.md` 署名报告；禁商用库（onetake）在交付环节被硬性拦截。

## 快速开始

```bash
pip install -e .                    # 需要 Python 3.10+
brew install ffmpeg                 # 渲染合成
pip install edge-tts                # 配音（可选）

# 1. 建项目
filmforge new 奶茶店-发布会
cd 奶茶店-发布会
#    编辑 brief.md（客户需求）和 storyboard.json（分镜）

# 2. 组装生成提示词，丢给 Claude Code 生成 film.html
filmforge brief prompt --style enterprise-blue > prompt.md
#    Claude Code 按 prompt.md 生成 films/film.html

# 3. 逐帧渲染成片
filmforge render films/film.html -o 成片-无声.mp4 --duration 30

# 4. 配音 + 混音
filmforge brief voice              # 列出分镜配音文本
filmforge voice "让每一帧都有价值" -o vo.mp3
filmforge compose 成片-无声.mp4 -o final.mp4 --audio vo.mp3

# 5. 合规交付（成片 + 源文件 + 署名报告）
filmforge deliver . -o dist/
```

## 工作原理

```
brief.md + storyboard.json（分镜：时间轴/文案/配音/动效）
        │  filmforge brief prompt
        ▼
Claude Code 生成 film.html（frame(t) 驱动，?t= 支持静止帧）
        │  filmforge render（headless Chrome 逐帧截图 + ffmpeg）
        ▼
成片-无声.mp4 ── filmforge voice / compose（edge-tts + ffmpeg 混音）
        │  filmforge deliver
        ▼
dist/ = 成片.mp4 + films 源文件 + storyboard.json + attribution.md
```

## 内置风格

| 风格 | 说明 |
|---|---|
| `enterprise-blue` 深空蓝·企业发布 | 科技公司/产品发布/融资路演：几何构成、数字滚动、缓动节奏规范（原创，MIT） |

新增风格：`filmforge new 项目名` 后在项目 `styles/` 目录按 `style.json + prompt.md + example.html` 三件套扩展；开源库风格用 `filmforge sources` 查看许可后按各自文档引入。

## 服务定价（作品集见 site/）

| 档位 | 价格 | 内容 |
|---|---|---|
| 基础 | ¥3,000/条 | 30s 内、1 风格、配音配乐、2 轮修改 |
| 标准 | ¥8,000/条 | 60s 内、风格样片 3 选 1、定制分镜、3 轮修改、源文件 |
| 定制 | ¥15,000 起 | 90s+、专属风格开发、实拍混剪 |

## 路线图

见 [PLAN.md](PLAN.md)。Phase 0（本仓库）已完成管线与作品集，下一步：接 3 单跑通交付 SOP。

## License

MIT。第三方开源库的许可与署名要求以 `filmforge sources` 与交付包内 `attribution.md` 为准。
