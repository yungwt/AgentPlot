"""布局 Agent：为每页规划版式、文字块与配图，并归一化页码。"""
import json
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.core.settings import llm_settings
from backend.schemas.layout_schema import LayoutOutline, SlideLayout


class LayoutPlannerAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=llm_settings.LLM_MODEL,
            api_key=llm_settings.LLM_API_KEY,
            base_url=llm_settings.LLM_BASE_URL,
            temperature=0.4,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "请根据完整PPT内容，自由规划每页布局：\n\n{enriched_json}"),
        ])
        self.chain = self.prompt | self.llm

    def _get_system_prompt(self) -> str:
        return """你是一位资深的PPT视觉设计师。你的任务是为每页幻灯片自由规划布局，你会收到关于内容页的明细，但封面页需要你自己按要求生成，最终生成的页数将是内容页数+1（封面）。

【唯一硬性约束】
- **文字块之间不能重叠**
- **文字块与图片不能重叠**
- 幻灯片尺寸为 13.33 × 7.5 英寸
- 所有元素必须完全在画布内：0 ≤ x ≤ 13.33，0 ≤ y ≤ 7.5
- 所有坐标(x, y)和尺寸(width, height)单位为英寸
- 根据主题选择一个主题色,后续所有页面都要基于这个色调,尽量不要选择以白色作为主题色
- 所有颜色值必须使用十六进制格式，如 #FFFFFF、#3498DB
- 至少有一半的内容页要有图片
- 每一页都有有合理的装饰元素

【关键要求：文字直接嵌入】
- 每个 text_block 必须包含 "text" 字段，把对应的文字内容直接放入
- 不要只写引用，要把完整文字嵌入JSON中
- 文字内容来自输入数据中的 title、subtitle、paragraphs 等字段

【设计哲学】
- 你拥有完全的设计自由，根据内容自然决定版式
- 信息密度决定版式复杂度：内容少则留白大气，内容多则紧凑有序
- 配色、字体、背景色完全由你自由选择
- 整体风格统一，配色协调，相邻页面版式可呼应但不过于雷同
- 整个ppt要有统一背景色，根据主题灵活调整，而不是每页都白色


【封面页 — 第0页必须遵守】
- page_type 固定为 "cover"
- 居中布局，必须包含：PPT总主题 + 副标题/描述
- 所有元素必须完全在画布内：0 ≤ x ≤ 13.33，0 ≤ y ≤ 7.5
- 标题：大字号（36-48pt），粗体
- 副标题：中等字号（18-24pt），常规
- 图片可选，需要就加，不需要就省略
- 适当设计一些美化元素，使得封面不单调

【内容页】
- page_type 固定为 "content"
- 版式自由选择：单栏、双栏、上下分割、网格、时间线等,但是不能大量内容页使用同一个版式
- 图片可选，需要就加，不需要就省略
- decoration 可选

【图片类型 — 必须严格遵守】
当需要添加图片时，必须根据内容选择正确的 chart_type，不能随意填写：

SVG 类型（数据精确、结构清晰，用于图表和流程图）：
- bar_chart: 柱状图，展示数据对比
- line_chart: 折线图，展示趋势变化
- pie_chart: 饼图，展示占比关系
- flowchart: 流程图，展示步骤流程
- architecture: 架构图，展示系统结构
- timeline: 时间线，展示时间顺序
- concept_map: 概念图，展示概念关系
- matrix: 矩阵图，展示二维对比
- comparison: 对比图，展示差异对比

PNG 类型（视觉丰富、美观演示，用于配图和装饰）：
- illustration: 插画/配图
- landscape: 风景/场景图
- product: 产品图
- icon: 图标
- decoration: 装饰元素
- photo: 照片/实拍
- abstract: 抽象艺术图

【选择规则】
- 数据、流程、结构、对比 → 用 SVG 类型
- 视觉、氛围、装饰、场景 → 用 PNG 类型

【输出格式】
严格返回JSON，无其他文字：

封面页示例：
{{
    "page_number": 0,
    "page_type": "cover",
    "layout_type": "cover",
    "background_color": "#FFFFFF",
    "text_blocks": [
        {{
            "text": "2026年AI大模型行业趋势分析",
            "position": {{"x": 1.665, "y": 2.8}},
            "size": {{"width": 10, "height": 1.2}},
            "style": {{
                "font_size": 40,
                "font_weight": "bold",
                "color": "#2C3E50",
                "alignment": "center"
            }}
        }},
        {{
            "text": "从技术突破到商业落地的完整路径",
            "position": {{"x": 1.665, "y": 4.3}},
            "size": {{"width": 8, "height": 0.8}},
            "style": {{
                "font_size": 22,
                "font_weight": "normal",
                "color": "#3498DB",
                "alignment": "center"
            }}
        }}
    ],
    "decorations": [
        {{
            "type": "line",
            "position": {{"x": 4.165, "y": 3.6}},
            "size": {{"width": 5, "height": 0.02}},
            "color": "#3498DB",
            "description": "标题下方装饰线"
        }}
    ]
}}

内容页示例：
{{
    "page_number": 1,
    "page_type": "content",
    "layout_type": "双栏",
    "background_color": "#FFFFFF",
    "text_blocks": [
        {{
            "text": "全球AI市场规模持续高速增长",
            "position": {{"x": 1.0, "y": 1.0}},
            "size": {{"width": 5.0, "height": 0.8}},
            "style": {{
                "font_size": 28,
                "font_weight": "bold",
                "color": "#2C3E50",
                "alignment": "left"
            }}
        }},
        {{
            "text": "2024年突破2000亿美元，预计2026年将达到5000亿美元，年复合增长率超过50%。",
            "position": {{"x": 1.0, "y": 2.2}},
            "size": {{"width": 5.0, "height": 2.0}},
            "style": {{
                "font_size": 16,
                "font_weight": "normal",
                "color": "#333333",
                "alignment": "left"
            }}
        }}
    ],
    "image": {{
        "description": "横向柱状图展示2024-2026年全球AI市场规模，2024年2000亿，2025年3200亿，2026年5000亿",
        "chart_type": "bar_chart",
        "position": {{"x": 7.0, "y": 1.5}},
        "size": {{"width": 5.5, "height": 4.5}},
        "fit_mode": "contain"
    }}
}}

最终输出示例：
{{
    "topic": "PPT总主题",
    "total_pages": 总页数,
    "slides": [
        {{...封面页...}},
        {{...内容页...}},
        {{...内容页...}}
    ]
}}

注意：image 和 decorations 都是可选的，不需要时直接省略该字段。
"""

    def _clean_json_string(self, raw_text: str) -> str:
        """去掉 markdown 代码块围栏"""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _parse_json_with_fallback(self, raw_text: str) -> dict:
        """解析 LLM 返回的 JSON：直接解析 → 括号截取 → json_repair 兜底。

        不用正则去"修复"JSON：单引号替换等正则会把正文里的撇号一起改坏，
        而 json_repair 能安全处理尾逗号、缺引号键名、前后夹杂的说明文字。
        """
        text = self._clean_json_string(raw_text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 截取首个 { 到最后一个 } 之间的内容，去掉 JSON 前后的说明文字
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        import json_repair
        data = json_repair.repair_json(text, return_objects=True)
        if isinstance(data, dict):
            return data

        print("⚠️ 无法解析 JSON，原始内容（最后 300 字符）:")
        print(text[-300:])
        raise ValueError("无法解析 LLM 返回的 JSON，请检查原始输出")

    def _normalize_page_numbers(self, parsed: dict) -> None:
        """页码归一化：封面 = 0，内容页从 1 顺序递增。

        提示词原设计就是封面第 0 页（图片文件名为 page_{N}，N 指第 N 个
        内容页）。封面不能占 1，否则与首个内容页撞号，按页码定位会取错页。
        按类型识别封面（而不是按下标），封面不在首位时也成立。
        """
        seen_cover = False
        content_seq = 0
        for slide in parsed.get("slides", []):
            is_cover = (not seen_cover) and (
                slide.get("page_type") == "cover"
                or slide.get("layout_type") == "cover"
            )
            if is_cover:
                slide["page_number"] = 0
                seen_cover = True
            else:
                content_seq += 1
                slide["page_number"] = content_seq

    def run(self, enriched: dict) -> LayoutOutline:
        response = self.chain.invoke({
            "enriched_json": json.dumps(enriched, ensure_ascii=False),
        })

        parsed = self._parse_json_with_fallback(response.content)
        self._normalize_page_numbers(parsed)

        slides = [SlideLayout(**s) for s in parsed["slides"]]
        return LayoutOutline(
            topic=enriched.get("topic", ""),
            total_pages=len(slides),
            slides=slides,
        )
