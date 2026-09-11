"""统一导出三个阶段的数据模型。

各模块直接从子模块导入（如 `schemas.layout_schema`），这里的 re-export
仅供外部便捷引用。
"""
from .content_schema import PPTContentOutline, SlideContent
from .enriched_schema import EnrichedOutline, EnrichedSlideContent
from .layout_schema import LayoutOutline

__all__ = [
    # 大纲阶段
    "SlideContent",
    "PPTContentOutline",
    # 撰写阶段
    "EnrichedSlideContent",
    "EnrichedOutline",
    # 布局阶段
    "LayoutOutline",
]
