"""大纲 Agent：把用户需求重构为 PPT 文案大纲（结构化输出）。"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.core.settings import llm_settings
from backend.schemas.content_schema import PPTContentOutline, SlideContent


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
        # 单页补全用的 LLM（结构化输出到 SlideContent，prompt 独立）
        self.single_structured_llm = self.llm.with_structured_output(SlideContent)
        self.single_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_single_system_prompt()),
            ("user", self._get_single_user_prompt()),
        ])
        self.single_chain = self.single_prompt | self.single_structured_llm

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
        outline = self.structured_llm.invoke(messages)
        return self._enforce_page_count(outline, page_count, user_request)

    # --- 页数对齐（补全 / 截断）-----------------------------------------
    #
    # 现象：LLM 经常给不足的 slides 数（如 3 页只给 1 页 + 空 bullet_points），
    # 现有 schema / prompt 都只是软约束，偷懒的 LLM 会照过。下游 content_writer /
    # layout_planner / ppt_builder 一路基于 outline 自然缩水，最终 PPT 页数对不上
    # 用户请求。
    #
    # 这里在拿到 outline 后做硬对齐：不足就循环补全单页，超出就截断。原 prompt /
    # schema 一律不动，补全走独立的 single_chain（结构化输出到 SlideContent）。

    def _enforce_page_count(self, outline: PPTContentOutline, page_count: int,
                            user_request: str) -> PPTContentOutline:
        slides = list(outline.slides or [])

        # 超出：截断（按 page_number 升序，取前 page_count 个，避免 LLM 把 page_number
        # 写成 1..N 但数组更长时误删前面的）
        if len(slides) > page_count:
            slides = sorted(slides, key=lambda s: s.page_number)[:page_count]
            outline.slides = slides
            outline.total_pages = page_count
            return outline

        # 已对齐：原样返回
        if len(slides) == page_count:
            outline.total_pages = page_count
            return outline

        # 不足：循环补全缺失页
        # 已有 page_number 集合（防御性去重 + 跳号）
        existing_numbers = sorted({s.page_number for s in slides})
        existing_titles = [s.title for s in slides]
        # 缺失页码：从 1 开始递增，凡是 existing_numbers 里没出现的就是缺的
        missing = [n for n in range(1, page_count + 1)
                   if n not in set(existing_numbers)]
        # 如果 missing 算不出（比如 LLM 把 page_number 写成 5,6,7 等大数），
        # 就以"现有最大号 + 1"为基准补到 page_count
        if not missing and len(slides) < page_count:
            next_num = (max(existing_numbers) if existing_numbers else 0) + 1
            missing = list(range(next_num, next_num + (page_count - len(slides))))

        for target_page in missing:
            try:
                new_slide = self._generate_one_slide(
                    user_request=user_request,
                    topic=outline.topic,
                    existing_titles=existing_titles,
                    target_page=target_page,
                )
            except Exception as exc:  # 单页补全失败不能拖垮整次：记下、用占位
                new_slide = SlideContent(
                    page_number=target_page,
                    title=f"补充要点 {target_page}",
                    subtitle="（自动补全）",
                    bullet_points=[f"待补充要点（{exc!s}）"],
                )
            # 强制用目标页码覆盖 LLM 返回值，避免 LLM 不按 prompt 写 page_number
            # 破坏后续 sort / 截断语义
            new_slide.page_number = target_page
            slides.append(new_slide)
            existing_titles.append(new_slide.title)

        slides = sorted(slides, key=lambda s: s.page_number)[:page_count]
        outline.slides = slides
        outline.total_pages = page_count
        return outline

    def _get_single_system_prompt(self) -> str:
        return """你是 PPT 策划助手，专门补全大纲中缺失的单页。

                【硬性要求】
                1. 严格遵守字数限制：title ≤ 12 字、subtitle ≤ 20 字、bullet_points 每项 ≤ 25 字、每页最多 6 项
                2. 结论先行：title 是核心结论，不是描述性标题
                3. 与已有页面形成明确逻辑推演关系，不要重复
                4. 输出必须是合法 JSON，可被解析
                """

    def _get_single_user_prompt(self) -> str:
        return """原 PPT 主题：{topic}

                已生成的页面：
                {existing_titles_block}

                请生成第 {target_page} 页（保持与前后页面的逻辑连贯）。

                严格返回 JSON：
                {{
                  "page_number": {target_page},
                  "title": "本页结论（≤12字）",
                  "subtitle": "副标题或核心结论（≤20字）",
                  "bullet_points": ["要点1（≤25字）", "要点2（≤25字）"]
                }}
                """

    def _generate_one_slide(self, user_request: str, topic: str,
                             existing_titles: list, target_page: int) -> SlideContent:
        titles_block = "\n".join(
            f"  - 第 {i + 1} 页：{t}" for i, t in enumerate(existing_titles)
        )
        messages = self.single_prompt.format_messages(
            topic=topic or user_request,
            existing_titles_block=titles_block or "（暂无）",
            target_page=target_page,
        )
        slide = self.single_structured_llm.invoke(messages)
        # model_copy 防御性：避免上游 chain 返回的对象在多次 invoke 间被复用
        # （真实场景不会，但单测 stub 会，导致相邻 slide.page_number 互相覆盖）
        return slide.model_copy()
