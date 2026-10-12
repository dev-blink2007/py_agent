import os


COMMUNITY_BASE_URL = os.getenv(
    "COMMUNITY_BASE_URL",
    "http://127.0.0.1:8080"
).strip().rstrip("/")       #rstrip("/")：去掉地址末尾的 /，方便后面拼接路径

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-flash"
).strip()