# AgentPlot — AI 多智能体协同 PPT 生成器

> 📊 输入一个主题，五个 AI 智能体自动协作，生成一份结构完整、图文并茂的专业 PPT 演示文稿。

## 项目简介

AgentPlot 是一个基于**多智能体（Multi-Agent）架构**的智能 PPT 生成系统。用户只需提供一个主题（如"大语言模型的基本原理"），系统便会通过一条由五个专职 Agent 组成的流水线，自动完成从大纲策划到最终 PPT 文件输出的全流程。

本项目为**自然语言处理（NLP）课程期末考查项目**。

## 系统架构

```
用户输入主题
     │
     ▼
┌─────────────┐    outline.json    ┌──────────────────┐   enriched.json   ┌─────────────────┐
│  ① Planner  │ ─────────────────▶ │ ② Content Writer │ ────────────────▶ │ ③ Layout Planner│
│   大纲策划   │                    │    内容扩写       │                   │    布局规划      │
└─────────────┘                    └──────────────────┘                   └─────────────────┘
                                                                                 │
                                              ┌──────────────────────────────────┘
                                              ▼
                              ┌───────────────────────────────┐
                              │        图片类型分流判断          │
                              └───────────────┬───────────────┘
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                    ┌──────────────────┐           ┌──────────────────┐
                    │ ④ SVG Engine     │           │ ⑤ PNG Engine     │
                    │   SVG 图表引擎    │           │   PNG 配图引擎    │
                    │ (柱状图/流程图等)  │           │ (插画/风景等)     │
                    └────────┬─────────┘           └────────┬─────────┘
                             │                              │
                             └──────────────┬───────────────┘
                                            ▼
                                   ┌─────────────────┐   output.pptx
                                   │  ⑥ PPT Builder   │
                                   │    PPT 组装引擎   │
                                   └──────────────────┘
```

## 五个智能体

| # | Agent | 文件 | 职责 | 技术要点 |
|---|-------|------|------|---------|
| ① | **PPTPlannerAgent** | `src/agents/planner.py` | 根据用户主题生成 PPT 大纲 | 支持联网搜索 + 思维链，结构化输出（Pydantic） |
| ② | **PPTContentWriterAgent** | `src/agents/content_writer.py` | 将大纲扩写为丰富的段落内容 | 全局视角扩写，避免页面间重复 |
| ③ | **LayoutPlannerAgent** | `src/agents/layout_planner.py` | 为每页规划视觉布局、配色、图片位置 | 多策略 JSON 解析 + 自动修复 |
| ④ | **SVGEngineAgent** | `src/agents/svg_engine.py` | 生成 SVG 图表（柱状图、流程图、饼图等） | LLM 直接生成 SVG 代码 |
| ⑤ | **PNGEngineAgent** | `src/agents/png_engine.py` | 生成 PNG 配图（插画、风景、产品图等） | 调用通义万相图像生成 API |
| ⑥ | **PPT Builder** | `generation/ppt_builder.py` | 将所有元素组装为 .pptx 文件 | python-pptx + Playwright SVG 渲染 |

## 数据流水线

每一步的输出都保存为 JSON 文件，支持断点续跑和分步调试：

```
output/session_xxxxxxxxx/
├── config.json       # 用户配置（主题、页数）
├── outline.json      # Step 1: 大纲
├── enriched.json     # Step 2: 扩写内容
├── layout.json       # Step 3: 布局规划
├── images/           # Step 4: 生成的图片
│   ├── page_1.svg
│   ├── page_2.png
│   └── ...
└── output.pptx       # Step 5: 最终 PPT 文件
```

## 快速开始

### 环境要求

- Python 3.10+
- Playwright（用于 SVG 转 PNG 渲染）

### 安装

```bash
# 1. 克隆项目
git clone <repo-url>
cd AgentPlot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器（SVG 渲染需要）
playwright install chromium

# 4. 配置 API Key
#    复制 .env 文件并填入你的 API 配置
```

### 配置 `.env`

```env
LLM_MODEL=qwen3.7-max-2026-05-20
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 运行方式

#### 方式一：Streamlit Web 界面（推荐）

```bash
streamlit run app.py
```

在浏览器中打开后：
1. 在左侧输入 PPT 主题并设置页数
2. 选择"逐步运行"或"一键全部运行"
3. 在每个 Tab 页查看中间结果和最终 PPT
4. 支持重置到任意步骤、重新生成单页图片

#### 方式二：命令行批量测试

```bash
python run.py
```

内置三个测试样例，自动批量运行并输出到 `output/` 目录。

## 测试样例

| # | 主题 | 测试点 |
|---|------|--------|
| 1 | 中山大学的发展历程 | 中文历史类主题 + 时间线图表 |
| 2 | 咖啡豆到咖啡的生产链流程图 | SVG 流程图生成能力 |
| 3 | YouTube vs TikTok vs Kuaishou | 英文主题 + 数据对比图表 |

## 核心特性

- **多智能体协同**：五个专职 Agent 各司其职，流水线协作
- **图片智能分流**：图表类（SVG 引擎）和配图类（PNG 引擎）自动区分
- **分步可控**：每一步结果可视化，支持断点续跑和单步重置
- **单页重生成**：可对单页图片删除并重新生成，无需重跑全流程
- **联网搜索增强**：大纲生成阶段支持联网搜索获取实时信息
- **思维链推理**：大纲生成支持深度思考模式，提升逻辑质量
- **鲁棒 JSON 解析**：布局 Agent 内置多策略 JSON 解析与自动修复
- **结构化数据校验**：全流程使用 Pydantic 模型保证数据一致性

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM 框架 | LangChain + ChatOpenAI (OpenAI 兼容接口) |
| 数据模型 | Pydantic |
| Web 界面 | Streamlit |
| PPT 生成 | python-pptx |
| SVG 渲染 | Playwright (Chromium) |
| 图像生成 | 通义万相 (qwen-image-2.0-pro) |
| 图片处理 | Pillow |

## 项目结构

```
AgentPlot/
├── app.py                      # Streamlit Web 应用主入口
├── run.py                      # 命令行批量测试脚本
├── .env                        # API 配置（需自行创建）
├── requirements.txt            # Python 依赖
│
├── src/
│   ├── agents/                 # 多智能体模块
│   │   ├── planner.py          # ① 大纲生成 Agent
│   │   ├── content_writer.py   # ② 内容扩写 Agent
│   │   ├── layout_planner.py   # ③ 布局规划 Agent
│   │   ├── svg_engine.py       # ④ SVG 图表生成 Agent
│   │   └── png_engine.py       # ⑤ PNG 图片生成 Agent
│   └── schemas/                # Pydantic 数据模型
│       ├── content_schema.py   # 大纲数据模型
│       ├── enriched_schema.py  # 扩写内容模型
│       └── layout_schema.py    # 布局数据模型
│
├── generation/
│   └── ppt_builder.py          # ⑥ PPT 文件组装引擎
│
├── config/
│   └── settings.py             # 全局配置（从 .env 加载）
│
└── output/                     # 生成输出目录
    └── session_xxxxxxxxx/
```

## 许可证

本项目为课程作业，仅供学习交流使用。
