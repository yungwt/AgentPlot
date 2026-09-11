# src/schemas/content_schema.py
from pydantic import BaseModel, Field
from typing import List

class SlideContent(BaseModel):
    page_number: int = Field(description="当前幻灯片的页码，从 1 开始")
    title: str = Field(description="单页核心大标题，要求极度精炼，严格控制在 12 个字以内")
    subtitle: str = Field(description="单页副标题或核心结论，严格控制在 20 个字以内")
    bullet_points: List[str] = Field(
        description="当前页的核心论点列表，最多不能超过 6 项，每项严格控制在 25 个字以内（适合排版）",
        max_items=6
    )

class PPTContentOutline(BaseModel):
    topic: str = Field(description="PPT 的总主题")
    total_pages: int = Field(description="PPT 的总页数")
    slides: List[SlideContent] = Field(description="它是整份 PPT 所有页面的精炼内容集合")