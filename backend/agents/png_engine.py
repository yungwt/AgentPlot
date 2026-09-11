"""PNG 图片引擎：调用通义万相生成位图，下载后裁剪到目标尺寸。"""
import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import requests
from PIL import Image

from backend.core.settings import llm_settings


class PNGEngineAgent:
    def __init__(self):
        self.model_name = "qwen-image-2.0-pro-2026-06-22"
        self.api_key = llm_settings.LLM_API_KEY

        # 构建正确的 API URL
        base_url = getattr(llm_settings, "LLM_BASE_URL", "https://dashscope.aliyuncs.com")
        if "dashscope" in base_url:
            self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        else:
            self.api_url = f"{base_url}/api/v1/services/aigc/multimodal-generation/generation"

    def _build_prompt(self, image_spec: dict) -> str:
        """构建提示词"""
        description = image_spec.get("description", "")

        style = image_spec.get("style", "professional")
        style_map = {
            "modern": "现代极简风格",
            "professional": "专业商务风格",
            "creative": "创意设计风格",
            "vibrant": "活力明亮风格",
        }
        style_text = style_map.get(style, "专业商务风格")

        colors = image_spec.get("colors", [])
        color_text = f"，配色使用 {', '.join(colors)}" if colors else ""

        theme = image_spec.get("theme", {})
        theme_text = ""
        if theme.get("primary"):
            theme_text += f"，主色 {theme['primary']}"
        if theme.get("secondary"):
            theme_text += f"，辅色 {theme['secondary']}"

        return f"{description}，{style_text}{color_text}{theme_text}，清晰简洁，适合PPT展示。严禁包含文字标签和水印。"

    def _get_generation_size(self, image_spec: dict) -> tuple:
        """计算用于模型生成图片的尺寸，返回 (gen_width, gen_height) 像素。

        模型要求生成面积在 512² ~ 2048² 之间，超出范围则等比缩放。
        """
        width_in = image_spec.get("size", {}).get("width", 5.5)
        height_in = image_spec.get("size", {}).get("height", 4.0)
        w = int(width_in * 96)
        h = int(height_in * 96)

        MIN_AREA, MAX_AREA = 512 ** 2, 2048 ** 2
        area = w * h
        scale = 1.0
        if area < MIN_AREA:
            scale = (MIN_AREA / area) ** 0.5
        elif area > MAX_AREA:
            scale = (MAX_AREA / area) ** 0.5

        gen_w = max(int(w * scale), 512)
        gen_h = max(int(h * scale), 512)
        if scale != 1.0:
            print(f"   📐 生成尺寸 {w}*{h} 超出面积限制，等比缩放为 {gen_w}*{gen_h}")
        return gen_w, gen_h

    def _extract_image_url(self, data: dict) -> str:
        """从响应中提取图片URL"""
        try:
            choices = data.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", [])
                for item in content:
                    if isinstance(item, dict) and "image" in item:
                        return item["image"]
            return None
        except Exception:
            return None

    def _download_and_resize(self, url: str, target_width: int, target_height: int) -> str:
        """下载图片并调整到目标尺寸，返回 base64"""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return None

            img = Image.open(BytesIO(response.content))
            if img.size != (target_width, target_height):
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"   ⚠️ 下载/调整图片失败: {e}")
            return None

    def _save_image(self, image_data: str, output_path: str) -> bool:
        """保存 base64 图片到文件"""
        try:
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            return True
        except Exception as e:
            print(f"   ⚠️ 保存图片失败: {e}")
            return False

    def _call_api_sync(self, prompt: str, gen_width: int, gen_height: int) -> dict:
        """同步调用API"""
        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]}
                ]
            },
            "parameters": {
                "result_format": "message",
                "watermark": False,
                "prompt_extend": True,
                "size": f"{gen_width}*{gen_height}",
                "negative_prompt": "低分辨率，低画质，肢体畸形，画面过饱和，无质感，低级AI感，扭曲，不合常理的排版，杂乱标签",
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
        if response.status_code == 200:
            return response.json()
        print(f"   ⚠️ API调用失败: {response.status_code}")
        print(f"   {response.text[:200]}")
        return None

    async def arun(self, image_spec: dict) -> str:
        """异步生成PNG图片，返回 base64 数据；失败返回空串"""
        prompt = self._build_prompt(image_spec)
        gen_width, gen_height = self._get_generation_size(image_spec)

        width_in = image_spec.get("size", {}).get("width", 5.5)
        height_in = image_spec.get("size", {}).get("height", 4.0)
        target_width = int(width_in * 96)
        target_height = int(height_in * 96)

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                response_data = await loop.run_in_executor(
                    executor, self._call_api_sync, prompt, gen_width, gen_height,
                )

            if not response_data:
                print("   ⚠️ API返回为空")
                return ""
            image_url = self._extract_image_url(response_data)
            if not image_url:
                print("   ⚠️ 无法提取图片URL")
                return ""
            image_data = self._download_and_resize(image_url, target_width, target_height)
            if not image_data:
                print("   ⚠️ 图片调整失败")
                return ""
            return image_data
        except Exception as e:
            print(f"   ⚠️ 图片生成失败: {type(e).__name__}: {e}")
            return ""

    def run(self, image_spec: dict) -> str:
        """同步调用"""
        return asyncio.run(self.arun(image_spec))

    async def arun_and_save(self, image_spec: dict, output_path: str) -> bool:
        """生成图片并保存到指定路径"""
        image_data = await self.arun(image_spec)
        if not image_data:
            return False
        return self._save_image(image_data, output_path)
