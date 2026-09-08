# run.py（项目根目录）
import os
import json
import asyncio
from src.agents.planner import PPTPlannerAgent
from src.agents.content_writer import PPTContentWriterAgent
from src.agents.layout_planner import LayoutPlannerAgent
from src.agents.svg_engine import SVGEngineAgent
from generation.ppt_builder import generate_ppt
from src.agents.png_engine import PNGEngineAgent


# ==================== 测试样例 ====================
TEST_CASES = [
    "中山大学的发展历程",
    "绘制SVG流程图，展示从一颗咖啡豆到一杯咖啡的完整生产链(种植、采摘、烘焙、研磨、冲煮)",
    "YouTube has 10 times more videos than TikTok, TikTok has 2 times more than Kuaishou"
]

PAGE_COUNT = 3
BASE_OUTPUT_DIR = "output"
# =================================================


def process_single_case(user_request: str, case_index: int):
    """处理单个测试样例"""
    # 每个样例放在自己的文件夹
    case_name = f"case_{case_index + 1}"
    output_dir = os.path.join(BASE_OUTPUT_DIR, case_name)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"📌 测试样例 {case_index + 1}: {user_request[:50]}...")
    print(f"📁 输出目录: {output_dir}")
    print(f"{'='*60}\n")
    
    # Step 1: 大纲
    print("🔷 Step 1: 生成大纲")
    planner = PPTPlannerAgent(enable_web_search=True, enable_thinking=True)
    outline = planner.run(user_request, page_count=PAGE_COUNT)
    with open(os.path.join(output_dir, "outline.json"), "w", encoding="utf-8") as f:
        json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(output_dir, "outline.json"), "r", encoding="utf-8") as f:
        outline = json.load(f)
    
    # Step 2: 内容
    print("🔷 Step 2: 内容扩写")
    writer = PPTContentWriterAgent()
    enriched = writer.run(outline)
    with open(os.path.join(output_dir, "enriched.json"), "w", encoding="utf-8") as f:
        json.dump(enriched.model_dump(), f, ensure_ascii=False, indent=2)
    
    # Step 3: 布局规划
    print("🔷 Step 3: 布局规划")
    with open(os.path.join(output_dir, "enriched.json"), "r", encoding="utf-8") as f:
        enriched = json.load(f)
    
    layout_agent = LayoutPlannerAgent()
    layout = layout_agent.run(enriched)
    with open(os.path.join(output_dir, "layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout.model_dump(), f, ensure_ascii=False, indent=2)
    
    print(f"✅ 布局完成 | 共 {layout.total_pages} 页\n")
    
    # Step 4: 分流生成图片
    print("🔷 Step 4: 分流生成图片")
    
    with open(os.path.join(output_dir, "layout.json"), "r", encoding="utf-8") as f:
        layout = json.load(f)
    
    # 统一图片目录
    image_dir = os.path.join(output_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    
    # 定义类型分类
    PNG_TYPES = {
        "illustration", "landscape", "product",
        "icon", "decoration", "photo", "abstract"
    }
    
    # 分类任务
    svg_tasks = []
    png_tasks = []
    
    for slide in layout["slides"]:
        if not slide.get("image"):
            continue
        chart_type = slide["image"].get("chart_type", "illustration")
        if chart_type in PNG_TYPES:
            png_tasks.append(slide)
        else:
            svg_tasks.append(slide)
    
    print(f"   📊 SVG任务: {len(svg_tasks)} 张 → 保存为 .svg")
    print(f"   🖼️ PNG任务: {len(png_tasks)} 张 → 保存为 .png")
    
    # 1. 生成 SVG
    if svg_tasks:
        from src.agents.svg_engine import SVGEngineAgent
        
        async def _gen_svg(slide):
            page = slide["page_number"]
            agent = SVGEngineAgent()
            svg = await agent.arun(slide["image"])
            path = os.path.join(image_dir, f"page_{page}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"      ✅ 第{page}页 SVG 已生成")
        
        async def _gen_all_svg():
            await asyncio.gather(*[asyncio.create_task(_gen_svg(s)) for s in svg_tasks])
        
        asyncio.run(_gen_all_svg())
    
    # 2. 生成 PNG
    if png_tasks:
        from src.agents.png_engine import PNGEngineAgent
        
        async def _gen_png(slide):
            page = slide["page_number"]
            agent = PNGEngineAgent()
            path = os.path.join(image_dir, f"page_{page}.png")
            success = await agent.arun_and_save(slide["image"], path)
            print(f"      {'✅' if success else '⚠️'} 第{page}页 PNG {'已生成' if success else '生成失败'}")
        
        async def _gen_all_png():
            await asyncio.gather(*[asyncio.create_task(_gen_png(s)) for s in png_tasks])
        
        asyncio.run(_gen_all_png())
    
    print(f"\n✅ 图片生成完成 | SVG: {len(svg_tasks)} 张, PNG: {len(png_tasks)} 张")
    print(f"📁 图片目录: {image_dir}")
    
    # Step 5: 生成 PPT
    print("🔷 Step 5: 生成 PPT")
    generate_ppt(
        layout_path=os.path.join(output_dir, "layout.json"),
        image_dir=image_dir,
        output_path=os.path.join(output_dir, "output.pptx")
    )
    
    print(f"\n✅ 样例 {case_index + 1} 完成: {output_dir}")


def main():
    print(f"\n{'='*60}")
    print(f"🚀 开始批量测试 | 共 {len(TEST_CASES)} 个样例")
    print(f"{'='*60}\n")
    
    for i, user_request in enumerate(TEST_CASES):
        try:
            process_single_case(user_request, i)
        except Exception as e:
            print(f"\n❌ 样例 {i+1} 失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print(f"✅ 全部测试完成 | 共 {len(TEST_CASES)} 个样例")
    print(f"📁 输出目录: {BASE_OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()