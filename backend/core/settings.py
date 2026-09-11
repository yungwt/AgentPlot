import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录：backend/core/settings.py 的祖父级
BASE_DIR = Path(__file__).resolve().parents[2]
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

OUTPUT_DIR = BASE_DIR / "output"

# 大模型 (LLM) API 配置
class LLMSettings:
    LLM_MODEL: str = os.getenv("LLM_MODEL")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")

llm_settings = LLMSettings()
