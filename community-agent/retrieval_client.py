import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


def fetch_semantic_posts(query):
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "error": "语义查询内容必须是非空字符串",
            "retryable": False,
        }

    query = query.strip()

    if len(query) > 500:
        return {
            "ok": False,
            "error": "语义查询内容不能超过500个字符",
            "retryable": False,
        }

    base_url = os.getenv(
        "RETRIEVAL_BASE_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")

    body = json.dumps(
        {"query": query, "top_k": 3},
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        url=f"{base_url}/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=15
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        return {
            "ok": False,
            "error": "语义检索接口返回错误",
            "status": error.code,
            "retryable": (
                error.code in (408, 429)
                or 500 <= error.code < 600
            ),
        }

    except TimeoutError:
        return {
            "ok": False,
            "error": "语义检索请求超时",
            "retryable": True,
        }

    except urllib.error.URLError:
        return {
            "ok": False,
            "error": "无法连接语义检索服务",
            "retryable": True,
        }

    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "ok": False,
            "error": "语义检索服务返回了无法解析的数据",
            "retryable": False,
        }

    # 当前接口约定：成功时返回 data.posts 列表。
    if (
        not isinstance(payload, dict)
        or payload.get("ok") is not True
        or not isinstance(payload.get("data"), dict)
        or not isinstance(payload["data"].get("posts"), list)
    ):
        return {
            "ok": False,
            "error": "语义检索服务返回结构不符合约定",
            "retryable": False,
        }

    return payload