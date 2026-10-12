import json
import urllib.request
import urllib.error
import urllib.parse
from config import COMMUNITY_BASE_URL


def fetch_post_detail(post_id):
    url = f"{COMMUNITY_BASE_URL}/api/post/{post_id}"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            response_text = response.read().decode("utf-8")

        payload = json.loads(response_text)
        post = payload["data"]

        return {
            "ok": True,
            "data": {
                "id": post["id"],
                "title": post["title"],
                "content": post["content"]
            }
        }

    except urllib.error.HTTPError as error:
        messages = {
            400: "帖子ID不合法",
            404: "帖子不存在",
            500: "社区服务查询失败"
        }

        return {
            "ok": False,
            "error": messages.get(
                error.code,
                "社区详情接口返回错误"
            ),
            "status": error.code,
            "retryable": error.code in (429, 500, 502, 503, 504)
        }

    except urllib.error.URLError as error:
        return {
            "ok": False,
            "error": "无法连接社区服务",
            "detail": str(error.reason),
            "retryable": True
        }

    except TimeoutError:
        return {
            "ok": False,
            "error": "社区详情请求超时",
            "retryable": True
        }

def fetch_post_list(keyword):
    params = urllib.parse.urlencode({ #urlencode() 会把中文、空格、& 等字符编码成适合 URL 查询参数的形式。这样不会把关键词里的 & 误当成参数分隔符
        "keyword": keyword,
        "page": 1,
        "size": 5
    })
    url = f"{COMMUNITY_BASE_URL}/api/posts?{params}"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            response_text = response.read().decode("utf-8")

    except urllib.error.HTTPError as error:
        return {
            "ok": False,
            "error": "社区搜索接口返回错误",
            "status": error.code
        }

    except urllib.error.URLError as error:
        return {
            "ok": False,
            "error": "无法连接社区服务",
            "detail": str(error.reason)
        }

    except TimeoutError:
        return {"ok": False, "error": "社区搜索请求超时"}

    payload = json.loads(response_text)

    summaries = []
    for post in payload["data"]:
        summaries.append({"id": post["id"], "title": post["title"]})

    # ② 返回结果，结构见下方。
    return {
        "ok": True,
        "data": {
            "posts": summaries,
            "total": payload["total"],
            "page": payload["page"],
            "size": payload["size"]
        }
    }


if __name__ == "__main__":
    print(fetch_post_list("孙颖莎"))
    print(fetch_post_list("不存在的主题XYZ"))