# agents/svg_engine.py
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config.settings import llm_settings
import asyncio

class SVGEngineAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=llm_settings.LLM_MODEL,
            api_key=llm_settings.LLM_API_KEY,
            base_url=llm_settings.LLM_BASE_URL,
            temperature=0.2  
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt()),
            ("user", "请根据图片需求描述生成SVG：\n\n{image_spec}")
        ])
        self.chain = self.prompt | self.llm

    def _system_prompt(self):
        return """你是专业的SVG图表生成引擎。根据图片描述生成纯净的SVG代码。

【核心要求】
- 只输出完整的SVG代码，不要任何解释文字
- viewBox 自适应内容，保留合理边距
- 颜色使用现代配色，对比度清晰
- 文字使用 sans-serif 字体

【尺寸约束】
- viewBox 必须严格按照给定的 svg_width × svg_height 设置
- 所有元素坐标和尺寸在此范围内，不留外部空白

【图表类型指南】
- bar_chart: 柱状图，含坐标轴、数值标签、图例
- line_chart: 折线图，含数据点、网格线
- pie_chart: 饼图，含百分比标签
- flowchart: 流程图，节点+箭头，圆角矩形
- diagram: 示意图，简洁抽象

【输出格式】
直接输出SVG代码，以 <svg> 开头，</svg> 结尾。
"""

    def _extract_svg(self, raw: str) -> str:
        text = raw.strip()
        # 去 markdown 代码块
        if "```" in text:
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        # 提取 <svg>...</svg>
        match = re.search(r"<svg[\s\S]*?</svg>", text)
        svg = match.group(0) if match else text
    
        # 去重复属性（简单处理：保留第一个）
        svg = re.sub(r'(y2="[^"]*")\s+y2="[^"]*"', r'\1', svg)
        
        return svg
    
    def run(self, image_spec: dict) -> str:
        return asyncio.run(self.arun(image_spec))

    async def arun(self, image_spec: dict) -> str:
        width_in = image_spec.get("size", {}).get("width", 5.5)
        height_in = image_spec.get("size", {}).get("height", 4.0)
        
        prompt_data = {
            **image_spec,
            "svg_width": int(width_in * 96),
            "svg_height": int(height_in * 96),
        }
        
        response = await self.chain.ainvoke({
            "image_spec": json.dumps(prompt_data, ensure_ascii=False)
        })
        return self._extract_svg(response.content)