# AgentPlot — AI 多智能体协同 PPT 生成器

> 📊 输入一个主题，五个 AI 智能体自动协作，生成一份结构完整、图文并茂的专业 PPT 演示文稿。

## 项目简介

AgentPlot 是一个基于**多智能体（Multi-Agent）架构**的智能 PPT 生成系统。用户只需提供一个主题（如"大语言模型的基本原理"），系统便会通过一条由五个专职 Agent 组成的流水线，自动完成从大纲策划到最终 PPT 文件输出的全流程。

系统采用 **FastAPI 后端 + Vue 3 前端** 的现代前后端分离架构，支持长任务异步执行、断点续跑、单步重置、单页图片重生成与会话管理。

本项目为**自然语言处理（NLP）课程期末考查项目**。

## 系统架构

```
用户输入主题 (Vue 3 + Naive UI)
       │
       ▼                                                                            
  ┌─────────────┐   outline.json    ┌──────────────────┐   enriched.json              
  │ ① Planner   │ ────────────────▶│ ② Content Writer │ ──────────────▶  ┌──────────┐
  │   大纲策划  |                    │    内容扩写       │                  │ ③ Layout │ 
  └─────────────┘                   └──────────────────┘                  │  Planner │ 
                                                                          └─────┬────┘ 
                                                                                │     
                                            ┌───────────────────────────────────┘      
                                            ▼  layout.json                            
                              ┌───────────────────────────────┐                      
                              │        图片类型分流判断         │                      
                              └───────────────┬───────────────┘                        
                                              │                                        
                              ┌───────────────┴───────────────┐                      
                              ▼                               ▼                        
                    ┌──────────────────┐           ┌──────────────────┐                
                    │ ④ SVG Engine     │           │ ⑤ PNG Engine     │                 
                    │   SVG 图表引擎   │            │   PNG 配图引擎   │                 
                    │ (柱状图/流程图等) │            │ (插画/风景等)    │                 
                    └────────┬─────────┘           └────────┬─────────┘                 
                             │                              │                          
                             └──────────────┬───────────────┘                          
                                            ▼                                          
                                   ┌─────────────────┐    output.pptx                   
                                   │  ⑥ PPT Builder  │ ──────────────▶ /static/output 
                                   │    PPT 组装引擎  │                               
                                   └─────────────────┘                                  

```

## 五个智能体

| #  | Agent                  | 文件                                | 职责                       | 技术要点                                  |
|----|------------------------|-------------------------------------|----------------------------|-------------------------------------------|
| ①  | **PPTPlannerAgent**    | `backend/agents/planner.py`         | 根据用户主题生成 PPT 大纲   | 支持联网搜索 + 思维链，结构化输出 (Pydantic) |
| ②  | **ContentWriterAgent** | `backend/agents/content_writer.py`  | 将大纲扩写为丰富的段落内容 | 全局视角扩写，避免页面间重复              |
| ③  | **LayoutPlannerAgent** | `backend/agents/layout_planner.py`  | 为每页规划视觉布局、配色   | 多策略 JSON 解析 + 自动修复              |
| ④  | **SVGEngineAgent**     | `backend/agents/svg_engine.py`      | 生成 SVG 图表              | LLM 直接生成 SVG 代码                     |
| ⑤  | **PNGEngineAgent**     | `backend/agents/png_engine.py`      | 生成 PNG 配图              | 调用通义万相图像生成 API                   |
| ⑥  | **PPT Builder**        | `backend/services/ppt_builder.py`   | 将所有元素组装为 .pptx     | python-pptx + Playwright SVG 渲染         |

## 数据流水线

每一步的输出都保存为 JSON 文件，支持断点续跑、分步调试和单步重置：

```
output/session_<timestamp>/
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

> **页码约定**：封面 = 第 0 页，内容页从 1 开始顺序递增。图片文件按内容页编号命名，
> 即 `images/page_{N}.{png|svg}`，封面不参与编号。

## 快速开始

### 环境要求

- **Python 3.10+**（推荐 3.11 / 3.13）
- **Node.js 18+**（推荐 20 / 22）
- **Playwright**（用于 SVG 转 PNG 渲染）

### 1. 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（仅首次）
playwright install chromium
```

### 2. 前端

```bash
cd frontend
npm install
```

### 3. 配置 `.env`

在项目根目录创建 `.env`，填入你的 LLM / 图像生成 API 配置：

```env
LLM_MODEL=qwen3.7-max-2026-05-20
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 4. 启动

启动两个进程（分别在不同终端中运行）：

```bash
# 终端 1：后端 (默认 http://127.0.0.1:8000)
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2：前端 (默认 http://127.0.0.1:5173，会把 /api 与 /static 代理到后端)
cd frontend
npm run dev
```

浏览器打开 <http://127.0.0.1:5173> 即可使用。

### 5. 一键启动（可选）

如果你喜欢写一个脚本同时拉起两端，可以把上面的两条命令塞进同一个 shell 或用
[concurrently](https://www.npmjs.com/package/concurrently) 等工具——但这不是必需的。

## 前端功能

Vue 3 + Naive UI（暗色主题），主要交互：

| 区域       | 功能                                                                 |
|------------|----------------------------------------------------------------------|
| 侧边栏     | 创建会话（3–10 页）、切换历史会话、重置到任意步骤、**删除会话**       |
| 顶部进度条 | 五步流水线可视化：当前步骤呼吸光晕、已完成步骤绿色辉光                 |
| 内容 Tab   | 大纲 / 扩写 / 布局 / 图片 / PPT 五个 Tab 分步查看产物                 |
| 单页重生成 | 在「图片」Tab 选中页码 → 重新生成该页图片，无需重跑全流程              |
| 错误提示   | FastAPI 422 detail 列表、字符串等多种格式友好展示                     |

## 后端 API

所有路由挂在 `/api/sessions` 前缀下。生成类接口返回 `{job_id}`，通过轮询 `jobs/{job_id}`
获取实时状态（`pending → running → success/error`）。

| 方法     | 路径                                                | 说明                       |
|----------|-----------------------------------------------------|----------------------------|
| `GET`    | `/api/sessions`                                     | 列出所有会话（历史）       |
| `POST`   | `/api/sessions`                                     | 创建新会话                 |
| `GET`    | `/api/sessions/{id}`                                | 会话元数据 + 步骤完成状态  |
| `DELETE` | `/api/sessions/{id}`                                | 删除整个会话               |
| `POST`   | `/api/sessions/{id}/reset`                          | 重置到指定步骤             |
| `GET`    | `/api/sessions/{id}/outline`                        | 大纲产物                   |
| `GET`    | `/api/sessions/{id}/content`                        | 扩写产物                   |
| `GET`    | `/api/sessions/{id}/layout`                         | 布局产物                   |
| `GET`    | `/api/sessions/{id}/images`                         | 图片清单                   |
| `GET`    | `/api/sessions/{id}/ppt`                            | 下载最终 .pptx             |
| `POST`   | `/api/sessions/{id}/steps/{step}`                   | 触发单个步骤（异步）       |
| `POST`   | `/api/sessions/{id}/images/{n}/regenerate`          | 单页图片重生成（异步）     |
| `DELETE` | `/api/sessions/{id}/images/{n}`                     | 删除单页图片               |
| `GET`    | `/api/sessions/{id}/jobs/{job_id}`                  | 查询异步任务状态           |

> 生成的图片 / PPT 都通过 `/static/output/<session_id>/...` 直接静态托管，无需鉴权。

## 项目结构

```
AgentPlot/
├── backend/                   # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── api/                   # HTTP 路由（sessions / steps）
│   ├── core/                  # settings / config / 内存 JobManager
│   ├── services/              # pipeline_service / session_io / artifacts / ppt_builder
│   ├── agents/                # 五个 LLM 智能体
│   └── schemas/               # Pydantic 数据模型
│
├── frontend/                  # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── components/        # TopBar / SidebarConfig / SideDrawer / StepBar / *Tab
│   │   ├── stores/            # Pinia: session.js / job.js
│   │   ├── api/               # axios 封装 + 拦截器
│   │   ├── styles/            # tokens.css（CSS 变量主题）
│   │   └── App.vue / main.js
│   ├── vite.config.js         # dev proxy: /api, /static → 127.0.0.1:8000
│   └── package.json
│
├── output/                    # 生成产物（被 .gitignore 排除）
│   └── session_<timestamp>/
│
├── requirements.txt           # Python 后端依赖
├── .env                       # API 配置（需自行创建，已 gitignore）
├── .gitignore
└── README.md
```

## 核心特性

- **多智能体协同**：五个专职 Agent 各司其职，流水线协作
- **图片智能分流**：图表类（SVG 引擎）和配图类（PNG 引擎）自动区分
- **分步可控**：每一步结果可视化，支持断点续跑和单步重置
- **单页重生成**：可对单页图片删除并重新生成，无需重跑全流程
- **异步长任务**：通过 BackgroundTasks + JobManager 异步执行，前端轮询状态
- **联网搜索增强**：大纲生成阶段支持联网搜索获取实时信息
- **思维链推理**：大纲生成支持深度思考模式，提升逻辑质量
- **鲁棒 JSON 解析**：布局 Agent 内置多策略 JSON 解析与自动修复
- **结构化数据校验**：全流程使用 Pydantic 模型保证数据一致性
- **会话管理**：支持多会话历史浏览、重置与删除

## 技术栈

| 组件          | 技术                                                  |
|---------------|-------------------------------------------------------|
| LLM 框架      | LangChain + ChatOpenAI (OpenAI 兼容接口)              |
| 数据模型      | Pydantic                                              |
| 后端          | FastAPI + Uvicorn                                     |
| 前端          | Vue 3 + Vite + Pinia + Naive UI（暗色主题）           |
| HTTP 客户端   | axios                                                |
| PPT 生成      | python-pptx                                           |
| SVG 渲染      | Playwright (Chromium)                                 |
| 图像生成      | 通义万相 (qwen-image-2.0-pro)                          |
| 图片处理      | Pillow                                               |

## 许可证

本项目为课程作业，仅供学习交流使用。
