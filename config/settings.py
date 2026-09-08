import os
from pathlib import Path
from dotenv import load_dotenv

# 基础路径配置 (利用 Path 自动计算项目根目录)

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)
# 过程产物输出目录
OUTPUT_DIR = BASE_DIR / "output"

# 大模型 (LLM) API 配置
class LLMSettings:
    LLM_MODEL: str = os.getenv("LLM_MODEL")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")

llm_settings = LLMSettings()
