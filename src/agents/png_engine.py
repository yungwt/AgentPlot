# agents/png_engine.py
import os
import json
import base64
import re
import requests
import asyncio
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from config.settings import llm_settings


class PNGEngineAgent:
    def __init__(self):
        self.model_name = "qwen-image-2.0-pro-2026-06-22"
        self.api_key = llm_settings.LLM_API_KEY
        
        # 构建正确的 API URL
        base_url = getattr(llm_settings, 'LLM_BASE_URL', 'https://dashscope.aliyuncs.com')
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
            "vibrant": "活力明亮风格"
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
        """
        计算用于模型生成图片的尺寸，确保面积符合要求
        返回: (gen_width, gen_height) 像素
        """
        # 原始目标尺寸（英寸转像素）
        width_in = image_spec.get("size", {}).get("width", 5.5)
        height_in = image_spec.get("size", {}).get("height", 4.0)
        target_width = int(width_in * 96)
        target_height = int(height_in * 96)
        
        # 模型要求：面积 262144 (512x512) ~ 4194304 (2048x2048) 像素
        min_area = 262144
        max_area = 4194304
        current_area = target_width * target_height
        
        # 如果面积已经在范围内，直接使用原尺寸
        if min_area <= current_area <= max_area:
            print(f"   📐 使用原始尺寸: {target_width}*{target_height} (面积: {current_area})")
            return target_width, target_height
        
        # 如果面积太小，按比例放大到最小面积
        if current_area < min_area:
            scale = (min_area / current_area) ** 0.5
            gen_width = int(target_width * scale)
            gen_height = int(target_height * scale)
            # 确保宽高至少512
            gen_width = max(gen_width, 512)
            gen_height = max(gen_height, 512)
            print(f"   📐 面积过小 ({current_area})，放大到 {gen_width}*{gen_height} (面积: {gen_width * gen_height})")
            return gen_width, gen_height
        
        # 如果面积太大，按比例缩小到最大面积
        if current_area > max_area:
            scale = (max_area / current_area) ** 0.5
            gen_width = int(target_width * scale)
            gen_height = int(target_height * scale)
            # 确保宽高至少512
            gen_width = max(gen_width, 512)
            gen_height = max(gen_height, 512)
            print(f"   📐 面积过大 ({current_area})，缩小到 {gen_width}*{gen_height} (面积: {gen_width * gen_height})")
            return gen_width, gen_height
        
        return target_width, target_height

    def _extract_image_url(self, data: dict) -> str:
        """从响应中提取图片URL"""
        try:
            choices = data.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", [])
                if content and isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "image" in item:
                            return item["image"]
            return None
        except Exception:
            return None

    def _download_and_resize(self, url: str, target_width: int, target_height: int) -> str:
        """
        下载图片并调整到目标尺寸，返回base64
        """
        try:
            # 下载原始图片
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            # 用 PIL 打开并调整尺寸
            img = Image.open(BytesIO(response.content))
            
            # 如果尺寸不匹配，调整到目标尺寸
            if img.size != (target_width, target_height):
                print(f"   🔄 调整图片尺寸: {img.size} → ({target_width}, {target_height})")
                # 使用高质量缩放
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 转为 PNG 并编码
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"   ⚠️ 下载/调整图片失败: {e}")
            return None

    def _save_image(self, image_data: str, output_path: str) -> bool:
        """保存base64图片到文件"""
        try:
            binary_data = base64.b64decode(image_data)
            with open(output_path, "wb") as f:
                f.write(binary_data)
            return True
        except Exception as e:
            print(f"   ⚠️ 保存图片失败: {e}")
            return False

    def _call_api_sync(self, prompt: str, gen_width: int, gen_height: int) -> dict:
        """同步调用API"""
        size_str = f"{gen_width}*{gen_height}"
        
        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "watermark": False,
                "prompt_extend": True,
                "size": size_str,
                "negative_prompt": "低分辨率，低画质，肢体畸形，画面过饱和，无质感，低级AI感，扭曲，不合常理的排版，杂乱标签"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.api_url,
            json=payload,
            headers=headers,
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ⚠️ API调用失败: {response.status_code}")
            print(f"   {response.text[:200]}")
            return None

    async def arun(self, image_spec: dict) -> str:
        """异步生成PNG图片，返回base64数据"""
        prompt = self._build_prompt(image_spec)
        
        # 获取生成尺寸和最终尺寸
        gen_width, gen_height = self._get_generation_size(image_spec)
        
        # 计算最终目标尺寸
        width_in = image_spec.get("size", {}).get("width", 5.5)
        height_in = image_spec.get("size", {}).get("height", 4.0)
        target_width = int(width_in * 96)
        target_height = int(height_in * 96)
        
        print(f"   📝 提示词: {prompt[:80]}...")
        print(f"   🎯 生成尺寸: {gen_width}*{gen_height} → 最终尺寸: {target_width}*{target_height}")
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                response_data = await loop.run_in_executor(
                    executor,
                    self._call_api_sync,
                    prompt,
                    gen_width,
                    gen_height
                )
            
            if response_data:
                image_url = self._extract_image_url(response_data)
                if image_url:
                    # 下载并调整到目标尺寸
                    image_data = self._download_and_resize(image_url, target_width, target_height)
                    if image_data:
                        print(f"   ✅ 图片生成并调整完成")
                        return image_data
                    else:
                        print(f"   ⚠️ 图片调整失败")
                else:
                    print(f"   ⚠️ 无法提取图片URL")
            else:
                print(f"   ⚠️ API返回为空")
            
            return ""
            
        except Exception as e:
            print(f"   ⚠️ 图片生成失败: {e}")
            return ""

    def run(self, image_spec: dict) -> str:
        """同步调用"""
        return asyncio.run(self.arun(image_spec))

    async def arun_and_save(self, image_spec: dict, output_path: str) -> bool:
        """生成图片并保存到指定路径"""
        image_data = await self.arun(image_spec)
        if image_data:
            return self._save_image(image_data, output_path)
        return False