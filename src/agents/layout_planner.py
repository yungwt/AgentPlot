# agents/layout_planner.py
import json
import re
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config.settings import llm_settings
from src.schemas.layout_schema import SlideLayout, LayoutOutline


class LayoutPlannerAgent:
    def __init__(self, style_hint: dict = None):
        self.style_hint = style_hint or {}
        self.llm = ChatOpenAI(
            model=llm_settings.LLM_MODEL,
            api_key=llm_settings.LLM_API_KEY,
            base_url=llm_settings.LLM_BASE_URL,
            temperature=0.4
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "请根据完整PPT内容，自由规划每页布局：\n\n{enriched_json}")
        ])
        self.chain = self.prompt | self.llm

    def _get_system_prompt(self) -> str:
        
        return """你是一位资深的PPT视觉设计师。你的任务是为每页幻灯片自由规划布局，你会收到关于内容页的明细，但封面页需要你自己安要求生成，最终生成的页数将是内容页数+1（封面）。

【唯一硬性约束】
- **文字块之间不能重叠**
- **文字块与图片不能重叠**
- 幻灯片尺寸为 13.33 × 7.5 英寸
- 所有元素必须完全在画布内：0 ≤ x ≤ 13.33，0 ≤ y ≤ 7.5
- 所有坐标(x, y)和尺寸(width, height)单位为英寸
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

【内容页】
- page_type 固定为 "content"
- 版式自由选择：单栏、双栏、上下分割、网格、时间线等
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
        """清理 LLM 返回的原始文本，提取 JSON"""
        text = raw_text.strip()
        
        # 1. 去掉 markdown 代码块
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        
        # 2. 提取 JSON（从第一个 { 开始，括号匹配）
        start = text.find('{')
        if start == -1:
            return text
        
        # 3. 括号匹配提取完整 JSON
        brace_count = 0
        in_string = False
        escape_next = False
        end = -1
        
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
        
        if end == -1:
            return text
        
        return text[start:end]

    def _repair_json(self, json_str: str) -> str:
        """修复常见的 JSON 问题"""
        # 1. 删除末尾多余的逗号（在 } 或 ] 前）
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 2. 修复没有引号的键名
        # 匹配类似 { key: value } 的情况，将 key 加上引号
        json_str = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # 3. 修复单引号（JSON 必须用双引号）
        # 先处理字符串内的单引号，暂时替换成占位符
        json_str = re.sub(r"'([^']*?)'", r'"\1"', json_str)
        
        # 4. 修复 page_number 为 0 的问题（改成 1）
        json_str = re.sub(r'"page_number":\s*0,', '"page_number": 1,', json_str)
        json_str = re.sub(r'"page_number":\s*0\s*}', '"page_number": 1}', json_str)
        
        return json_str

    def _parse_json_with_fallback(self, raw_text: str) -> Dict[str, Any]:
        """尝试多种方式解析 JSON"""
        # 先清理
        json_str = self._clean_json_string(raw_text)
        
        # 尝试直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 修复后解析
        try:
            repaired = self._repair_json(json_str)
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        
        # 打印错误信息用于调试
        print(f"⚠️ 无法解析 JSON，原始内容（最后 300 字符）:")
        print(json_str[-300:])
        
        # 尝试用 ast.literal_eval
        try:
            import ast
            data = ast.literal_eval(json_str)
            if isinstance(data, dict):
                return data
        except:
            pass
        
        # 最后尝试：用 json_repair 库
        try:
            import json_repair
            return json_repair.repair_json(json_str, return_objects=True)
        except:
            pass
        
        raise ValueError("无法解析 LLM 返回的 JSON，请检查原始输出")

    def run(self, enriched: dict) -> LayoutOutline:
        response = self.chain.invoke({
            "enriched_json": json.dumps(enriched, ensure_ascii=False)
        })
        
        print(f"LLM原始返回（前200字符）: {response.content[:200]}...")
        
        # 使用增强的 JSON 解析
        parsed = self._parse_json_with_fallback(response.content)
        
        # 修复页码从 0 开始的问题
        if "slides" in parsed:
            for i, slide in enumerate(parsed["slides"]):
                if slide.get("page_number", 0) == 0:
                    slide["page_number"] = i + 1
        
        slides = [SlideLayout(**s) for s in parsed["slides"]]
        return LayoutOutline(
            topic=enriched.get("topic", ""),
            total_pages=len(slides),
            slides=slides
        )