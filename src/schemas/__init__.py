# src/schemas/__init__.py
from .content_schema import (
    SlideContent,
    PPTContentOutline,
)

from .enriched_schema import (
    EnrichedSlideContent,
    EnrichedOutline
)
from .layout_schema import (
    LayoutOutline
)

__all__ = [
    # 大纲阶段
    "SlideContent",
    "PPTContentOutline",
    # 撰写阶段
    "EnrichedSlideContent",
    "EnrichedOutline",
    # 布局阶段
    "LayoutOutline",
    # 图片阶段
    "SVGCode",
]