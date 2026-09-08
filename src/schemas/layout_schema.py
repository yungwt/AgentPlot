from pydantic import BaseModel, Field
from typing import Optional
from typing import Optional, Literal

class TextStyle(BaseModel):
    font_size: int
    font_weight: str = "normal"  # 自由字符串
    color: str
    alignment: str = "left"  # 自由字符串
    font_family: Optional[str] = None


class TextBlock(BaseModel):
    text: str
    position: dict
    size: dict
    style: TextStyle



class ImageRequirement(BaseModel):
    description: str = Field(..., min_length=10, description="图片内容描述")
    
    # 严格限制图片类型
    chart_type: Literal[
        # SVG 类型（数据精确）
        "bar_chart", "line_chart", "pie_chart", 
        "flowchart", "architecture", "timeline",
        "concept_map", "matrix", "comparison",
        # PNG 类型（视觉丰富）
        "illustration", "landscape", "product",
        "icon", "decoration", "photo", "abstract"
    ] = Field(..., description="图片类型，决定生成引擎")
    
    position: dict = Field(..., description="坐标 x, y 单位英寸")
    size: dict = Field(..., description="尺寸 width, height 单位英寸")
    fit_mode: str = "contain"


class DecorativeElement(BaseModel):
    type: str  # 自由字符串，不再限制
    position: dict
    size: dict
    color: str
    description: str = ""


class SlideLayout(BaseModel):
    page_number: int
    page_type: str  # "cover" 或 "content"，自由字符串
    layout_type: str
    background_color: str
    text_blocks: list[TextBlock] = Field(..., min_length=1)
    image: Optional[ImageRequirement] = None
    decorations: list[DecorativeElement] = Field(default_factory=list)


class LayoutOutline(BaseModel):
    topic: str
    total_pages: int
    slides: list[SlideLayout]
    
    def get_cover(self) -> Optional[SlideLayout]:
        for slide in self.slides:
            if slide.page_type == "cover":
                return slide
        return None
    
    def get_content_pages(self) -> list[SlideLayout]:
        return [s for s in self.slides if s.page_type == "content"]