import os
from pathlib import Path

from dotenv import load_dotenv


# 根据当前文件的位置寻找 .env，不依赖终端所在目录。
ENV_FILE = Path(__file__).resolve().parent / ".env"

# 已存在的环境变量优先于 .env。
load_dotenv(ENV_FILE, override=False)


COMMUNITY_BASE_URL = os.getenv(
    "COMMUNITY_BASE_URL",
    "http://127.0.0.1:8080"
).strip().rstrip("/")

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-flash"
).strip()