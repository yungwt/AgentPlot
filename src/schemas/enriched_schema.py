# schemas/enriched_schema.py
from pydantic import BaseModel
from typing import Literal


class ParagraphBlock(BaseModel):
    type: Literal["concept", "example", "data", "contrast", "mechanism", "insight"]
    text: str


class EnrichedSlideContent(BaseModel):
    page_number: int
    title: str
    subtitle: str
    paragraphs: list[ParagraphBlock]


class EnrichedOutline(BaseModel):
    topic: str
    total_pages: int
    slides: list[EnrichedSlideContent]