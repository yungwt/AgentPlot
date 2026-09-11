"""大纲 Agent：把用户需求重构为 PPT 文案大纲（结构化输出）。"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.core.settings import llm_settings
from backend.schemas.content_schema import PPTContentOutline


class PPTPlannerAgent:
    def __init__(self, enable_web_search: bool = False, enable_thinking: bool = False):
        self.enable_web_search = enable_web_search
        self.enable_thinking = enable_thinking

        # 基础配置
        llm_kwargs = {
            "model": llm_settings.LLM_MODEL,
            "api_key": llm_settings.LLM_API_KEY,
            "base_url": llm_settings.LLM_BASE_URL,
            "temperature": 0.1,
        }

        # 构建 extra_body
        extra_body = {}
        if self.enable_thinking:
            extra_body["enable_thinking"] = True
        if self.enable_web_search:
            extra_body["enable_search"] = True

        # 统一传递（ChatOpenAI 会把 extra_body 平铺进请求体顶层，
        # 不能再包一层 {"extra_body": ...}，否则服务端收到嵌套字段静默忽略）
        if extra_body:
            llm_kwargs["extra_body"] = extra_body

        self.llm = ChatOpenAI(**llm_kwargs)
        self.structured_llm = self.llm.with_structured_output(PPTContentOutline)

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", self._get_user_prompt()),
        ])
        self.chain = self.prompt_template | self.structured_llm

    def _get_system_prompt(self) -> str:
        return """你是一位殿堂级的商务演示（PPT）策划专家。

                你的任务是将用户给出的主题，重构为逻辑严密、层级清晰的 PPT 文案大纲。

                【硬性黄金法则】
                1. 结论先行：每一页的title必须是核心结论，而非描述性标题
                2. 字数熔断：严格遵守字数限制！宁缺毋滥
                3. 页面连贯：前后页面必须具备明确的逻辑推演关系
                4. 禁止每页bullet_points数量完全相同（比如每页都3条），根据内容需求灵活调整
                5. 禁止所有bullet_points都是并列关系，应混合使用：因果、递进、对比、并列等
                6. 禁止生成罗列式大纲，必须体现"问题-分析-解决方案"或"现状-挑战-策略"等逻辑结构
                7.字数要严格遵守输出格式要求，title≤12字，subtitle≤20字，bullet_points每项≤25字，且每页最多6项

                【输出格式 - 必须严格遵守】
                你必须返回一个合法的 JSON 对象，格式如下：

                {{
                "topic": "PPT的总主题（简洁明了）",
                "total_pages": 3,
                "slides": [
                    {{
                    "page_number": 1,
                    "title": "第一页标题（≤12字）",
                    "subtitle": "副标题或核心结论（≤20字）",
                    "bullet_points": ["要点1（≤25字）", "要点2（≤25字）"]
                    }}
                ]
                }}

                【特别注意】
                - 字段名必须是 topic, total_pages, slides, page_number, title, subtitle, bullet_points
                - 不要使用其他字段名（如不要用 "content" 代替 "bullet_points"）
                - bullet_points 每页最多6项，每项不超过25字
                - 确保 JSON 格式完全合法，可以被解析
                """

    def _get_user_prompt(self) -> str:
        return """请为以下主题策划一份共 {page_count} 页的 PPT 大纲。

                主题需求：{user_request}

                请严格按照上述 JSON 格式返回 {page_count} 页的内容，确保：
                1. 每页的 page_number 从 1 开始递增
                2. 总页数等于 {page_count}
                3. 逻辑连贯，层层递进
                """

    def run(self, user_request: str, page_count: int = 3) -> PPTContentOutline:
        if not user_request or not user_request.strip():
            raise ValueError("主题需求不能为空")
        if not 1 <= page_count <= 20:
            raise ValueError("页数必须在 1-20 之间")

        messages = self.prompt_template.format_messages(
            user_request=user_request,
            page_count=page_count,
        )
        return self.structured_llm.invoke(messages)
