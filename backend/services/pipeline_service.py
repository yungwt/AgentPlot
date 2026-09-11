"""Pipeline runner: orchestrates the 5 agents + PPT builder.

Wraps the logic that was previously inlined in app.py / run.py so FastAPI
endpoints can trigger any single step. Async agent calls are run with
`asyncio.run` inside a worker thread (FastAPI BackgroundTasks are scheduled
via `run_in_threadpool` so this is safe).
"""
import asyncio
import json
from pathlib import Path

from backend.agents.content_writer import PPTContentWriterAgent
from backend.agents.layout_planner import LayoutPlannerAgent
from backend.agents.png_engine import PNGEngineAgent
from backend.agents.planner import PPTPlannerAgent
from backend.agents.svg_engine import SVGEngineAgent
from backend.services.ppt_builder import generate_ppt
from backend.services.session_io import session_dir

# 走 PNG 引擎的图片类型，其余 chart_type 走 SVG 引擎
PNG_TYPES = {
    "illustration", "landscape", "product",
    "icon", "decoration", "photo", "abstract",
}


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- Step 1: Outline ----------
def run_outline(session_id: str) -> dict:
    sdir = session_dir(session_id)
    cfg = _load_json(sdir / "config.json")
    planner = PPTPlannerAgent(enable_web_search=True, enable_thinking=True)
    outline = planner.run(cfg["user_request"], page_count=cfg["page_count"])
    data = outline.model_dump()
    _save_json(sdir / "outline.json", data)
    return {"slides": len(data.get("slides", []))}


# ---------- Step 2: Content ----------
def run_content(session_id: str) -> dict:
    sdir = session_dir(session_id)
    outline = _load_json(sdir / "outline.json")
    writer = PPTContentWriterAgent()
    enriched = writer.run(outline)
    data = enriched.model_dump()
    _save_json(sdir / "enriched.json", data)
    return {"slides": len(data.get("slides", []))}


# ---------- Step 3: Layout ----------
def run_layout(session_id: str) -> dict:
    sdir = session_dir(session_id)
    enriched = _load_json(sdir / "enriched.json")
    layout = LayoutPlannerAgent().run(enriched)
    data = layout.model_dump()
    _save_json(sdir / "layout.json", data)
    return {"total_pages": data.get("total_pages", len(data.get("slides", [])))}


# ---------- Step 4: Images ----------
def run_images(session_id: str) -> dict:
    sdir = session_dir(session_id)
    layout = _load_json(sdir / "layout.json")
    image_dir = sdir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    async def _gen_svg(agent, image_spec, out_path):
        svg = await agent.arun(image_spec)
        out_path.write_text(svg, encoding="utf-8")

    async def _gen_all():
        svg_agent, png_agent = SVGEngineAgent(), PNGEngineAgent()
        coros = []
        for slide in layout.get("slides", []):
            if not slide.get("image"):
                continue
            page = slide["page_number"]
            chart_type = slide["image"].get("chart_type", "illustration")
            if chart_type in PNG_TYPES:
                coros.append(png_agent.arun_and_save(
                    slide["image"], str(image_dir / f"page_{page}.png"),
                ))
            else:
                coros.append(_gen_svg(svg_agent, slide["image"], image_dir / f"page_{page}.svg"))
        if coros:
            await asyncio.gather(*coros)

    asyncio.run(_gen_all())
    return {"image_dir": str(image_dir)}


# ---------- Step 5: PPT ----------
def run_ppt(session_id: str) -> dict:
    sdir = session_dir(session_id)
    out = sdir / "output.pptx"
    generate_ppt(
        layout_path=str(sdir / "layout.json"),
        image_dir=str(sdir / "images"),
        output_path=str(out),
    )
    return {"ppt_path": str(out)}


# ---------- Single-image regeneration ----------
def regenerate_image(session_id: str, page_number: int) -> dict:
    sdir = session_dir(session_id)

    # PPT 已生成时禁止重生成图片（否则 PPT 会嵌旧图，需先重置到图片步骤）
    if (sdir / "output.pptx").exists():
        raise ValueError("PPT 已生成，请先在左侧重置到图片步骤，再重新生成图片")

    layout = _load_json(sdir / "layout.json")
    matches = [
        s for s in layout.get("slides", [])
        if s.get("page_number") == page_number
    ]
    if not matches:
        raise ValueError(f"未找到第 {page_number} 页")
    # 兼容历史 layout.json：早期页码修复逻辑会让封面与首个内容页同时是第 1 页。
    # 此时若直接取第一个匹配项会命中无图的封面，误报"该页没有图片"。
    # 因此优先取带 image 的那一条。
    target = next((s for s in matches if s.get("image")), matches[0])
    if not target.get("image"):
        raise ValueError(f"第 {page_number} 页没有图片")

    image_dir = sdir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    chart_type = target["image"].get("chart_type", "illustration")

    if chart_type in PNG_TYPES:
        async def _png() -> bool:
            return await PNGEngineAgent().arun_and_save(
                target["image"], str(image_dir / f"page_{page_number}.png"),
            )
        if not asyncio.run(_png()):
            # PNG engine 软失败：dashscope 业务错误/超时等被吞返回 ""
            # 必须 raise，让前端看到明确的失败提示
            raise RuntimeError(f"第 {page_number} 页图片生成失败，请重试")
        return {"page": page_number, "type": "png", "success": True}

    async def _svg() -> str:
        return await SVGEngineAgent().arun(target["image"])
    svg = asyncio.run(_svg())
    (image_dir / f"page_{page_number}.svg").write_text(svg, encoding="utf-8")
    return {"page": page_number, "type": "svg", "success": True}


def delete_image(session_id: str, page_number: int) -> bool:
    image_dir = session_dir(session_id) / "images"
    if not image_dir.exists():
        return False
    deleted = False
    for ext in (".png", ".svg", ".jpg", ".jpeg"):
        p = image_dir / f"page_{page_number}{ext}"
        if p.exists():
            p.unlink()
            deleted = True
    return deleted
