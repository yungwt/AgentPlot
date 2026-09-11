"""内容扩写 Agent：把大纲的 bullet_points 扩写成页内文本块。"""
import json
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.core.settings import llm_settings
from backend.schemas.enriched_schema import EnrichedOutline, EnrichedSlideContent


class PPTContentWriterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=llm_settings.LLM_MODEL,
            api_key=llm_settings.LLM_API_KEY,
            base_url=llm_settings.LLM_BASE_URL,
            temperature=0.4,
        )

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", "请根据完整PPT大纲，对每一页进行深度扩写：\n\n{outline_json}"),
        ])

        self.chain = self.prompt_template | self.llm

    def _get_system_prompt(self) -> str:
        return """你是一位资深PPT内容策划与科技撰稿人。

【核心任务】
接收完整PPT大纲（含 topic 和所有页面），对每一页进行深度扩写。

【全局视角原则】
- 理解每页在整个大纲中的位置和作用
- 页面间保持逻辑递进，前一页结论为后一页铺垫
- 避免不同页面重复内容，保持信息增量
- 术语首次出现时充分解释，后续页面可直接使用

【内容策略】
- 死扣subtitle：它是每页唯一核心观点，所有文本块为其提供论证支撑
- 验证方法：读完所有段落，subtitle是否仍成立且唯一
- 逻辑重组：根据bullet_points内在关系重构成独立文本块
- 块间关系：递进、并列、因果、对比
- 块内结构：中心句 + 解释或例证
- 信息密度：用具体事实替代空泛表述

【语言风格】
- 专业但不说教，术语准确但整体可读
- 禁用"首先/其次/然后/最后"等流水账连接词
- 禁用"在当今时代/随着发展/众所周知"等开场白
- 每块80字以内，长短错落，根据页内块数调整，避免大段文字

【输出格式】
严格返回JSON，无其他文字：
{{
    "slides": [
        {{
            "page_number": 1,
            "title": "原标题",
            "subtitle": "原副标题",
            "paragraphs": [
                {{"type": "concept | example | data | contrast | mechanism | insight", "text": "..."}}
            ]
        }}
    ]
}}
"""

    def _clean_json_string(self, raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n", "", text)
            text = re.sub(r"\n```$", "", text)
        return text.strip()

    def run(self, outline: dict) -> EnrichedOutline:
        try:
            response = self.chain.invoke({
                "outline_json": json.dumps(outline, ensure_ascii=False),
            })
            clean_json = self._clean_json_string(response.content)
            parsed_data = json.loads(clean_json)

            slides = [EnrichedSlideContent(**s) for s in parsed_data["slides"]]
            return EnrichedOutline(
                topic=outline.get("topic", ""),
                total_pages=len(slides),
                slides=slides,
            )
        except Exception as e:
            print(f"❌ ContentWriterAgent 扩充失败: {e}")
            raise
