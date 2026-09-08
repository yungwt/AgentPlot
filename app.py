# streamlit_app.py
import os
import json
import asyncio
import time
import streamlit as st
import pandas as pd
from PIL import Image
import base64
from io import BytesIO
import shutil
import re
# 导入 Agent
from src.agents.planner import PPTPlannerAgent
from src.agents.content_writer import PPTContentWriterAgent
from src.agents.layout_planner import LayoutPlannerAgent
from src.agents.svg_engine import SVGEngineAgent
from src.agents.png_engine import PNGEngineAgent
from generation.ppt_builder import generate_ppt
# 在文件顶部添加导入
from generation.ppt_builder import _svg_to_png
# ==================== 配置 ====================
PAGE_COUNT_DEFAULT = 3
BASE_OUTPUT_DIR = "output"

# 测试样例
EXAMPLE_CASES = [
    "大语言模型的基本原理",
    "通俗易懂地解释词向量(Word Embedding)的基本概念",
    "中山大学的发展历程",
    "绘制SVG流程图，展示从一颗咖啡豆到一杯咖啡的完整生产链(种植、采摘、烘焙、研磨、冲煮)",
    "YouTube has 10 times more videos than TikTok, TikTok has 2 times more than Kuaishou"
]

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="AI PPT 生成器",
    page_icon="📊",
    layout="wide"
)

# ==================== 初始化 Session State ====================
if "output_dir" not in st.session_state:
    st.session_state.output_dir = None
if "user_request" not in st.session_state:
    st.session_state.user_request = ""
if "page_count" not in st.session_state:
    st.session_state.page_count = PAGE_COUNT_DEFAULT
if "step" not in st.session_state:
    st.session_state.step = 0  # 0=未开始, 1=大纲, 2=内容, 3=布局, 4=图片, 5=完成
if "outline" not in st.session_state:
    st.session_state.outline = None
if "enriched" not in st.session_state:
    st.session_state.enriched = None
if "layout" not in st.session_state:
    st.session_state.layout = None
if "image_dir" not in st.session_state:
    st.session_state.image_dir = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "running" not in st.session_state:
    st.session_state.running = False
if "current_ppt_path" not in st.session_state:
    st.session_state.current_ppt_path = None

# ==================== 辅助函数 ====================
def get_output_dir():
    """获取当前输出目录"""
    if st.session_state.session_id:
        return os.path.join(BASE_OUTPUT_DIR, st.session_state.session_id)
    return None

def check_file_exists(filename):
    """检查文件是否存在"""
    output_dir = get_output_dir()
    if not output_dir:
        return False
    return os.path.exists(os.path.join(output_dir, filename))

def check_dir_exists(dirname):
    """检查目录是否存在"""
    output_dir = get_output_dir()
    if not output_dir:
        return False
    return os.path.exists(os.path.join(output_dir, dirname))

def get_current_available_step():
    """
    根据已存在的文件判断当前可执行的步骤
    返回: 0=未开始, 1=大纲, 2=内容, 3=布局, 4=图片, 5=PPT
    """
    if check_file_exists("outline.json"):
        if check_file_exists("enriched.json"):
            if check_file_exists("layout.json"):
                if check_dir_exists("images") and len(os.listdir(os.path.join(get_output_dir(), "images"))) > 0:
                    if check_file_exists("output.pptx"):
                        return 5  # 全部完成
                    return 4  # 可生成PPT
                return 3  # 可生成图片
            return 2  # 可生成布局
        return 1  # 可生成内容
    return 0  # 可生成大纲

def create_session(user_request, page_count):
    """创建新的会话"""
    session_id = f"session_{int(time.time())}"
    output_dir = os.path.join(BASE_OUTPUT_DIR, session_id)
    os.makedirs(output_dir, exist_ok=True)
    
    config = {
        "user_request": user_request,
        "page_count": page_count,
        "created_at": time.time()
    }
    with open(os.path.join(output_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    st.session_state.session_id = session_id
    st.session_state.output_dir = output_dir
    st.session_state.user_request = user_request
    st.session_state.page_count = page_count
    st.session_state.step = 0
    st.session_state.outline = None
    st.session_state.enriched = None
    st.session_state.layout = None
    st.session_state.image_dir = None
    st.session_state.current_ppt_path = None
    
    return output_dir

def load_step_data(step_name):
    """加载指定步骤的数据"""
    output_dir = get_output_dir()
    if not output_dir:
        return None
    
    file_map = {
        "outline": "outline.json",
        "enriched": "enriched.json",
        "layout": "layout.json"
    }
    
    if step_name not in file_map:
        return None
    
    file_path = os.path.join(output_dir, file_map[step_name])
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def reset_to_step(target_step):
    """
    重置到指定步骤，清除该步骤及之后的数据
    target_step: 0=未开始, 1=大纲, 2=内容, 3=布局, 4=图片, 5=PPT
    """
    output_dir = get_output_dir()
    if not output_dir:
        return
    
    # 清除步骤数据 - 删除目标步骤及之后的数据文件
    step_files = {
        1: "outline.json",
        2: "enriched.json",
        3: "layout.json",
        4: "images",
        5: "output.pptx"
    }
    
    # 删除目标步骤及之后的文件/目录
    for step in range(target_step, 6):
        if step in step_files:
            file_or_dir = os.path.join(output_dir, step_files[step])
            if os.path.exists(file_or_dir):
                if os.path.isdir(file_or_dir):
                    shutil.rmtree(file_or_dir)
                else:
                    os.remove(file_or_dir)
    
    # 更新 step 状态为目标步骤
    st.session_state.step = target_step
    
    # 清理对应的 session state
    if target_step <= 0:
        st.session_state.outline = None
        st.session_state.enriched = None
        st.session_state.layout = None
        st.session_state.image_dir = None
        st.session_state.current_ppt_path = None
    elif target_step <= 1:
        st.session_state.enriched = None
        st.session_state.layout = None
        st.session_state.image_dir = None
        st.session_state.current_ppt_path = None
        st.session_state.outline = load_step_data("outline")
    elif target_step <= 2:
        st.session_state.layout = None
        st.session_state.image_dir = None
        st.session_state.current_ppt_path = None
        st.session_state.outline = load_step_data("outline")
        st.session_state.enriched = load_step_data("enriched")
    elif target_step <= 3:
        st.session_state.image_dir = None
        st.session_state.current_ppt_path = None
        st.session_state.outline = load_step_data("outline")
        st.session_state.enriched = load_step_data("enriched")
        st.session_state.layout = load_step_data("layout")
    elif target_step <= 4:
        st.session_state.current_ppt_path = None
        st.session_state.outline = load_step_data("outline")
        st.session_state.enriched = load_step_data("enriched")
        st.session_state.layout = load_step_data("layout")
        image_dir = os.path.join(output_dir, "images")
        if os.path.exists(image_dir):
            st.session_state.image_dir = image_dir

def full_reset():
    """完全重置所有数据"""
    output_dir = get_output_dir()
    if output_dir and os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    st.session_state.session_id = None
    st.session_state.output_dir = None
    st.session_state.step = 0
    st.session_state.outline = None
    st.session_state.enriched = None
    st.session_state.layout = None
    st.session_state.image_dir = None
    st.session_state.current_ppt_path = None
    st.session_state.running = False

def delete_specific_image(page_number):
    """删除指定页的图片"""
    image_dir = os.path.join(st.session_state.output_dir, "images") if st.session_state.output_dir else None
    if not image_dir or not os.path.exists(image_dir):
        return False
    
    deleted = False
    for ext in ['.png', '.svg', '.jpg', '.jpeg']:
        img_path = os.path.join(image_dir, f"page_{page_number}{ext}")
        if os.path.exists(img_path):
            os.remove(img_path)
            deleted = True
    
    return deleted

def regenerate_image(page_number):
    """重新生成指定页的图片"""
    if not st.session_state.layout:
        return False, "请先生成布局"
    
    layout = st.session_state.layout
    target_slide = None
    for slide in layout.get('slides', []):
        if slide.get('page_number') == page_number:
            target_slide = slide
            break
    
    if not target_slide:
        return False, f"未找到第 {page_number} 页"
    
    if not target_slide.get('image'):
        return False, f"第 {page_number} 页没有图片"
    
    image_dir = os.path.join(st.session_state.output_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    
    chart_type = target_slide["image"].get("chart_type", "illustration")
    PNG_TYPES = {"illustration", "landscape", "product", "icon", "decoration", "photo", "abstract"}
    
    try:
        if chart_type in PNG_TYPES:
            async def _gen_png():
                agent = PNGEngineAgent()
                path = os.path.join(image_dir, f"page_{page_number}.png")
                success = await agent.arun_and_save(target_slide["image"], path)
                return success
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(_gen_png())
            loop.close()
            
            if success:
                return True, f"第 {page_number} 页图片已重新生成"
            else:
                return False, f"第 {page_number} 页图片生成失败"
        else:
            async def _gen_svg():
                agent = SVGEngineAgent()
                svg = await agent.arun(target_slide["image"])
                path = os.path.join(image_dir, f"page_{page_number}.svg")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                return True
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(_gen_svg())
            loop.close()
            
            if success:
                return True, f"第 {page_number} 页图片已重新生成"
            else:
                return False, f"第 {page_number} 页图片生成失败"
    except Exception as e:
        return False, f"生成失败: {str(e)}"

def render_svg(svg_path, caption=""):
    """渲染SVG文件为HTML"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        svg_content = re.sub(r'<\?xml.*?\?>', '', svg_content)
        
        st.markdown(f"""
        <div style="border: 1px solid #ddd; border-radius: 8px; padding: 10px; background: white; 
                    max-height: 500px; overflow: auto;">
            <div style="text-align: center;">
                {svg_content}
            </div>
            {f'<p style="text-align: center; margin: 5px 0; font-size: 12px; color: #666;">{caption}</p>' if caption else ''}
        </div>
        """, unsafe_allow_html=True)
        return True
    except Exception as e:
        st.warning(f"SVG 渲染失败: {e}")
        return False

def run_step_async(async_func):
    """运行异步函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(async_func)
        return result
    finally:
        loop.close()

# ==================== 运行函数 ====================
def run_outline(user_request, page_count, output_dir):
    """生成大纲"""
    with st.spinner("正在生成大纲..."):
        planner = PPTPlannerAgent(enable_web_search=True, enable_thinking=True)
        outline = planner.run(user_request, page_count=page_count)
        
        outline_path = os.path.join(output_dir, "outline.json")
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
        
        st.session_state.outline = outline.model_dump()
        st.session_state.step = 1
        return outline.model_dump()

def run_content(output_dir):
    """生成内容"""
    with st.spinner("正在扩写内容..."):
        outline_path = os.path.join(output_dir, "outline.json")
        with open(outline_path, "r", encoding="utf-8") as f:
            outline = json.load(f)
        
        writer = PPTContentWriterAgent()
        enriched = writer.run(outline)
        
        enriched_path = os.path.join(output_dir, "enriched.json")
        with open(enriched_path, "w", encoding="utf-8") as f:
            json.dump(enriched.model_dump(), f, ensure_ascii=False, indent=2)
        
        st.session_state.enriched = enriched.model_dump()
        st.session_state.step = 2
        return enriched.model_dump()

def run_layout(output_dir):
    """生成布局"""
    with st.spinner("正在规划布局..."):
        enriched_path = os.path.join(output_dir, "enriched.json")
        with open(enriched_path, "r", encoding="utf-8") as f:
            enriched = json.load(f)
        
        layout_agent = LayoutPlannerAgent()
        layout = layout_agent.run(enriched)
        
        layout_path = os.path.join(output_dir, "layout.json")
        with open(layout_path, "w", encoding="utf-8") as f:
            json.dump(layout.model_dump(), f, ensure_ascii=False, indent=2)
        
        st.session_state.layout = layout.model_dump()
        st.session_state.step = 3
        return layout.model_dump()

def run_images(output_dir):
    """生成图片"""
    with st.spinner("正在生成图片..."):
        layout_path = os.path.join(output_dir, "layout.json")
        with open(layout_path, "r", encoding="utf-8") as f:
            layout = json.load(f)
        
        image_dir = os.path.join(output_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        
        PNG_TYPES = {
            "illustration", "landscape", "product",
            "icon", "decoration", "photo", "abstract"
        }
        
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
        
        if svg_tasks:
            async def _gen_svg(slide):
                page = slide["page_number"]
                agent = SVGEngineAgent()
                svg = await agent.arun(slide["image"])
                path = os.path.join(image_dir, f"page_{page}.svg")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                return page
            
            async def _gen_all_svg():
                return await asyncio.gather(*[_gen_svg(s) for s in svg_tasks])
            
            run_step_async(_gen_all_svg())
        
        if png_tasks:
            async def _gen_png(slide):
                page = slide["page_number"]
                agent = PNGEngineAgent()
                path = os.path.join(image_dir, f"page_{page}.png")
                success = await agent.arun_and_save(slide["image"], path)
                return page, success
            
            async def _gen_all_png():
                return await asyncio.gather(*[_gen_png(s) for s in png_tasks])
            
            run_step_async(_gen_all_png())
        
        st.session_state.image_dir = image_dir
        st.session_state.step = 4
        return image_dir

def run_ppt(output_dir):
    """生成 PPT"""
    with st.spinner("正在生成 PPT..."):
        layout_path = os.path.join(output_dir, "layout.json")
        image_dir = os.path.join(output_dir, "images")
        output_path = os.path.join(output_dir, "output.pptx")
        
        generate_ppt(
            layout_path=layout_path,
            image_dir=image_dir,
            output_path=output_path
        )
        
        st.session_state.step = 5
        st.session_state.current_ppt_path = output_path
        return output_path

def run_all_steps(user_request, page_count, output_dir):
    """一次性运行所有步骤"""
    outline = run_outline(user_request, page_count, output_dir)
    st.success("✅ 大纲生成完成")
    
    enriched = run_content(output_dir)
    st.success("✅ 内容扩写完成")
    
    layout = run_layout(output_dir)
    st.success("✅ 布局规划完成")
    
    image_dir = run_images(output_dir)
    st.success("✅ 图片生成完成")
    
    ppt_path = run_ppt(output_dir)
    st.success("✅ PPT 生成完成")
    
    return ppt_path

# ==================== UI ====================

st.title("📊 AI PPT 智能生成器")
st.markdown("多智能体协同生成专业PPT演示文稿")

# ==================== 侧边栏：配置 ====================
with st.sidebar:
    st.header("⚙️ 配置")
    
    user_request = st.text_input(
        "📝 PPT 主题",
        value=st.session_state.user_request,
        placeholder="请输入PPT主题..."
    )
    
    st.markdown("**📌 快速示例**")
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLE_CASES):
        col = cols[i % 2]
        display_text = example[:18] + "..." if len(example) > 18 else example
        if col.button(display_text, key=f"example_{i}", use_container_width=True):
            st.session_state.user_request = example
            st.rerun()
    
    page_count = st.number_input(
        "📄 页数",
        min_value=1,
        max_value=10,
        value=st.session_state.page_count,
        step=1
    )
    
    st.divider()
    
    st.subheader("▶️ 运行控制")
    
    run_mode = st.radio(
        "选择运行模式",
        ["逐步运行", "一键全部运行"],
        help="逐步运行：每一步都可见结果，可随时调整\n一键全部运行：自动完成所有步骤"
    )
    
    if st.button("🚀 开始生成", type="primary", use_container_width=True):
        if not user_request:
            st.error("请输入PPT主题")
        else:
            st.session_state.running = True
            st.session_state.user_request = user_request
            st.session_state.page_count = page_count
            
            output_dir = create_session(user_request, page_count)
            
            if run_mode == "一键全部运行":
                with st.spinner("正在生成所有内容..."):
                    try:
                        ppt_path = run_all_steps(user_request, page_count, output_dir)
                        st.success(f"✅ 全部完成！PPT 已保存")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 生成失败: {e}")
                        st.session_state.running = False
            else:
                st.rerun()
    
    st.divider()
    
    st.subheader("🔄 重置控制")
    
    reset_target = st.selectbox(
        "重置到哪个步骤？",
        options=[
            ("未开始", 0),
            ("大纲", 1), 
            ("内容", 2),
            ("布局", 3),
            ("图片", 4),
            ("PPT", 5)
        ],
        format_func=lambda x: x[0],
        key="reset_target"
    )
    
    col_reset1, col_reset2 = st.columns(2)
    with col_reset1:
        if st.button("🔄 重置到选定步骤", use_container_width=True):
            target_step = reset_target[1]
            current_step = get_current_available_step()
            if target_step <= current_step:
                reset_to_step(target_step)
                st.success(f"已重置到 {reset_target[0]} 步骤")
                st.rerun()
            else:
                st.warning(f"当前步骤({current_step})在 {reset_target[0]} 之前，无需重置")
    
    with col_reset2:
        if st.button("🗑️ 清空所有数据", use_container_width=True, type="secondary"):
            full_reset()
            st.rerun()
    
    st.divider()
    
    st.subheader("📊 状态")
    steps = ["⏳ 未开始", "📋 大纲", "📝 内容", "📐 布局", "🖼️ 图片", "📦 完成"]
    current_step = get_current_available_step()
    st.progress(current_step / 5)
    st.write(f"当前步骤: **{steps[current_step]}**")
    
    if st.session_state.session_id:
        st.write(f"会话ID: `{st.session_state.session_id}`")

# ==================== 主区域 ====================

if st.session_state.output_dir:
    st.info(f"📁 当前会话: `{st.session_state.session_id}` | 输出目录: `{st.session_state.output_dir}`")

# ==================== 分步控制（基于文件存在性判断） ====================

output_dir = get_output_dir()
if output_dir and os.path.exists(output_dir):
    st.header("🔧 分步控制")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 检查各步骤文件是否存在
    has_outline = check_file_exists("outline.json")
    has_enriched = check_file_exists("enriched.json")
    has_layout = check_file_exists("layout.json")
    has_images = check_dir_exists("images") and len(os.listdir(os.path.join(output_dir, "images"))) > 0 if check_dir_exists("images") else False
    has_ppt = check_file_exists("output.pptx")
    
    # 大纲按钮 - 如果大纲不存在，显示可点击
    with col1:
        if not has_outline:
            if st.button("1️⃣ 大纲", use_container_width=True):
                try:
                    outline = run_outline(
                        st.session_state.user_request,
                        st.session_state.page_count,
                        st.session_state.output_dir
                    )
                    st.success("✅ 大纲生成完成")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")
        else:
            st.button("✅ 大纲已完成", disabled=True, use_container_width=True)
    
    # 内容按钮 - 如果大纲存在但内容不存在
    with col2:
        if has_outline and not has_enriched:
            if st.button("2️⃣ 内容", use_container_width=True):
                try:
                    enriched = run_content(st.session_state.output_dir)
                    st.success("✅ 内容扩写完成")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")
        elif has_enriched:
            st.button("✅ 内容已完成", disabled=True, use_container_width=True)
        else:
            st.button("2️⃣ 内容", disabled=True, use_container_width=True)
    
    # 布局按钮 - 如果内容存在但布局不存在
    with col3:
        if has_enriched and not has_layout:
            if st.button("3️⃣ 布局", use_container_width=True):
                try:
                    layout = run_layout(st.session_state.output_dir)
                    st.success("✅ 布局规划完成")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")
        elif has_layout:
            st.button("✅ 布局已完成", disabled=True, use_container_width=True)
        else:
            st.button("3️⃣ 布局", disabled=True, use_container_width=True)
    
    # 图片按钮 - 如果布局存在但没有图片
    with col4:
        if has_layout and not has_images:
            if st.button("4️⃣ 图片", use_container_width=True):
                try:
                    image_dir = run_images(st.session_state.output_dir)
                    st.success("✅ 图片生成完成")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")
        elif has_images:
            st.button("✅ 图片已完成", disabled=True, use_container_width=True)
        else:
            st.button("4️⃣ 图片", disabled=True, use_container_width=True)
    
    # PPT按钮 - 如果图片存在但PPT不存在
    with col5:
        if has_images and not has_ppt:
            if st.button("5️⃣ PPT", use_container_width=True):
                try:
                    ppt_path = run_ppt(st.session_state.output_dir)
                    st.success("✅ PPT 生成完成")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {e}")
        elif has_ppt:
            st.button("✅ PPT 已完成", disabled=True, use_container_width=True)
        else:
            st.button("5️⃣ PPT", disabled=True, use_container_width=True)

# ==================== 显示结果 ====================

tabs = st.tabs(["📋 大纲", "📝 内容", "📐 布局", "🖼️ 图片", "📦 PPT"])

# Tab 1: 大纲
with tabs[0]:
    if st.session_state.outline:
        st.subheader("📋 PPT 大纲")
        outline = st.session_state.outline
        
        st.write(f"**主题:** {outline.get('topic', '')}")
        st.write(f"**总页数:** {outline.get('total_pages', 0)}")
        
        for slide in outline.get('slides', []):
            with st.expander(f"第 {slide.get('page_number')} 页: {slide.get('title', '')}"):
                st.write(f"**副标题:** {slide.get('subtitle', '')}")
                st.write("**要点:**")
                for point in slide.get('bullet_points', []):
                    st.write(f"  • {point}")
        
        outline_path = os.path.join(st.session_state.output_dir, "outline.json")
        if os.path.exists(outline_path):
            with open(outline_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 下载大纲 JSON",
                    data=f.read(),
                    file_name="outline.json",
                    mime="application/json"
                )
    else:
        st.info("请先生成大纲")

# Tab 2: 内容
with tabs[1]:
    if st.session_state.enriched:
        st.subheader("📝 扩写内容")
        enriched = st.session_state.enriched
        
        for slide in enriched.get('slides', []):
            with st.expander(f"第 {slide.get('page_number')} 页: {slide.get('title', '')}"):
                st.write(f"**副标题:** {slide.get('subtitle', '')}")
                for para in slide.get('paragraphs', []):
                    st.write(f"  [{para.get('type', '')}] {para.get('text', '')}")
        
        enriched_path = os.path.join(st.session_state.output_dir, "enriched.json")
        if os.path.exists(enriched_path):
            with open(enriched_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 下载内容 JSON",
                    data=f.read(),
                    file_name="enriched.json",
                    mime="application/json"
                )
    else:
        st.info("请先生成内容")

# Tab 3: 布局 - 可视化改进
with tabs[2]:
    if st.session_state.layout:
        st.subheader("📐 布局规划")
        layout = st.session_state.layout
        
        total_slides = len(layout.get('slides', []))
        st.metric("总页数", total_slides)
        
        layout_types = {}
        for slide in layout.get('slides', []):
            layout_type = slide.get('layout_type', 'unknown')
            layout_types[layout_type] = layout_types.get(layout_type, 0) + 1
        
        if layout_types:
            st.write("**布局类型分布:**")
            cols = st.columns(min(len(layout_types), 4))
            for i, (layout_type, count) in enumerate(layout_types.items()):
                cols[i % len(cols)].metric(layout_type, count)
        
        st.divider()
        
        for slide in layout.get('slides', []):
            page_num = slide.get('page_number', 0)
            layout_type = slide.get('layout_type', '')
            page_type = slide.get('page_type', '')
            bg_color = slide.get('background_color', '#f0f0f0')
            
            with st.container():
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.markdown(f"""
                    <div style="
                        background-color: {bg_color};
                        padding: 10px;
                        border-radius: 8px;
                        text-align: center;
                        min-height: 80px;
                        border: 1px solid #ddd;
                    ">
                        <h3 style="margin: 0;">📄</h3>
                        <p style="margin: 5px 0; font-size: 14px; font-weight: bold;">第 {page_num} 页</p>
                        <p style="margin: 0; font-size: 12px; color: #666;">{layout_type}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    with st.expander(f"第 {page_num} 页 - {layout_type}", expanded=False):
                        text_blocks = slide.get('text_blocks', [])
                        if text_blocks:
                            st.write("**📝 文字内容预览:**")
                            for i, block in enumerate(text_blocks[:3]):
                                content = block.get('content', '')[:100]
                                if content:
                                    st.write(f"  • {content}...")
                        
                        if slide.get('image'):
                            img_info = slide['image']
                            chart_type = img_info.get('chart_type', '')
                            description = img_info.get('description', '')[:150]
                            st.write(f"**🖼️ 图片类型:** {chart_type}")
                            if description:
                                st.write(f"**描述:** {description}...")
                        
                        with st.expander("查看完整JSON"):
                            st.json(slide)
            
            st.divider()
        
        layout_path = os.path.join(st.session_state.output_dir, "layout.json")
        if os.path.exists(layout_path):
            with open(layout_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 下载布局 JSON",
                    data=f.read(),
                    file_name="layout.json",
                    mime="application/json"
                )
    else:
        st.info("请先生成布局")

# ==================== Tab 4: 图片 ====================
with tabs[3]:
    image_dir = os.path.join(st.session_state.output_dir, "images") if st.session_state.output_dir else None
    
    if image_dir and os.path.exists(image_dir):
        st.subheader("🖼️ 生成的图片")
        
        images = []
        for f in sorted(os.listdir(image_dir)):
            if f.endswith(('.png', '.svg', '.jpg', '.jpeg')):
                images.append(f)
        
        if images:
            st.write(f"共生成 **{len(images)}** 张图片")
            
            cols = st.columns(3)
            for i, img_file in enumerate(images):
                col = cols[i % 3]
                with col:
                    img_path = os.path.join(image_dir, img_file)
                    page_num = img_file.replace('page_', '').replace('.png', '').replace('.svg', '').replace('.jpg', '').replace('.jpeg', '')
                    
                    try:
                        if img_file.endswith('.png') or img_file.endswith('.jpg') or img_file.endswith('.jpeg'):
                            img = Image.open(img_path)
                            st.image(img, caption=f"第 {page_num} 页", use_container_width=True)
                        elif img_file.endswith('.svg'):
                            png_temp_path = os.path.join(image_dir, f"page_{page_num}_temp.png")
                            try:
                                success = _svg_to_png(
                                    svg_path=img_path,
                                    png_path=png_temp_path,
                                    w_in=8,
                                    h_in=6
                                )
                                
                                if success and os.path.exists(png_temp_path):
                                    img = Image.open(png_temp_path)
                                    st.image(img, caption=f"第 {page_num} 页 (SVG转PNG)", use_container_width=True)
                                else:
                                    st.warning(f"SVG 渲染失败，显示源代码")
                                    with open(img_path, 'r', encoding='utf-8') as f:
                                        svg_content = f.read()
                                    with st.expander(f"第 {page_num} 页 SVG 源代码"):
                                        st.code(svg_content[:500] + "...", language='xml')
                            except Exception as e:
                                st.warning(f"SVG 转换失败: {str(e)}")
                                with open(img_path, 'r', encoding='utf-8') as f:
                                    svg_content = f.read()
                                with st.expander(f"第 {page_num} 页 SVG 源代码"):
                                    st.code(svg_content[:500] + "...", language='xml')
                    except Exception as e:
                        st.warning(f"无法显示图片: {img_file} - {str(e)}")
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        with open(img_path, "rb") as f:
                            st.download_button(
                                label="📥 下载",
                                data=f.read(),
                                file_name=img_file,
                                key=f"download_img_{i}",
                                use_container_width=True
                            )
                    with col_btn2:
                        if st.button(f"🗑️ 删除", key=f"delete_img_{i}", use_container_width=True):
                            if delete_specific_image(int(page_num)):
                                st.success(f"已删除第 {page_num} 页图片")
                                st.rerun()
                            else:
                                st.error(f"删除第 {page_num} 页图片失败")
                    with col_btn3:
                        if st.button(f"🔄 重生成", key=f"regenerate_img_{i}", use_container_width=True):
                            success, message = regenerate_image(int(page_num))
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
        else:
            st.info("暂无图片")
    else:
        st.info("请先生成图片")

# Tab 5: PPT
with tabs[4]:
    output_path = st.session_state.current_ppt_path or (
        os.path.join(st.session_state.output_dir, "output.pptx") if st.session_state.output_dir else None
    )
    
    if output_path and os.path.exists(output_path):
        st.subheader("📦 生成的 PPT")
        
        file_size = os.path.getsize(output_path) / 1024
        st.write(f"**文件大小:** {file_size:.2f} KB")
        st.write(f"**文件路径:** `{output_path}`")
        
        with open(output_path, "rb") as f:
            st.download_button(
                label="📥 下载 PPT",
                data=f.read(),
                file_name="presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )
        
        st.divider()
        st.write("**📊 PPT 预览信息:**")
        
        layout_path = os.path.join(st.session_state.output_dir, "layout.json") if st.session_state.output_dir else None
        if layout_path and os.path.exists(layout_path):
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_data = json.load(f)
            
            slides = layout_data.get('slides', [])
            st.write(f"- **总页数:** {len(slides)}")
            
            st.write("**📑 页面列表:**")
            for slide in slides:
                page_num = slide.get('page_number', 0)
                layout_type = slide.get('layout_type', '')
                page_type = slide.get('page_type', '')
                has_image = "🖼️" if slide.get('image') else "📄"
                st.write(f"  {has_image} 第 {page_num} 页: {layout_type} ({page_type})")
        
    else:
        st.info("请先生成 PPT")

# ==================== 底部 ====================
st.divider()
st.caption("AI PPT 智能生成器 | 多智能体协同 | 支持分步调试 | 支持单页图片重新生成")