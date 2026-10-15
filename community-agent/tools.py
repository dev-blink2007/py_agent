import json
from community_client import fetch_post_detail, fetch_post_list
posts = [
    {"id": 1, "title": "GORM 连接池配置", "content": "介绍数据库连接池参数。"},
    {"id": 2, "title": "Redis 缓存入门", "content": "介绍缓存的基本使用。"},
    {"id": 3, "title": "排查数据库超时", "content": "记录 GORM 查询超时的排查过程。"}
]

def search_posts(keyword):
    if keyword == "":
        return []
    results = []
    for post in posts:
        if keyword in post["title"] or keyword in post["content"]:
            results.append({
            "id": post["id"],
            "title": post["title"]
        })
    return results

def execute_tool(tool_name, arguments_text):
    if tool_name not in ("search_posts", "fetch_post_detail"):
        return {"ok": False, "error": "未知工具"}

    try:
        arguments = json.loads(arguments_text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "工具参数不是合法 JSON"}

    if not isinstance(arguments, dict):
        return {"ok": False, "error": "工具参数必须是对象"}
    if tool_name == "search_posts":
        keyword = arguments.get("keyword")

        if not isinstance(keyword, str):
            return {"ok": False, "error": "关键词参数必须是字符串"}

        keyword = keyword.strip()
        if not keyword:
            return {"ok": False, "error": "搜索关键词不能为空"}

        return fetch_post_list(keyword)
    else:
        post_id = arguments.get("post_id")

        if type(post_id) is not int or post_id <= 0:
            return {"ok": False, "error": "post_id 必须是正整数"}

        return fetch_post_detail(post_id)

def get_post_detail(post_id):
    for post in posts:
        if post["id"] == post_id:
            return post
    return None
    
if __name__ == "__main__":
    print(execute_tool("search_posts", '{"keyword": "GORM"}'))
    print(execute_tool("search_posts", '{"keyword": 123}'))
    print(execute_tool("search_posts", '{}'))
    print(execute_tool("search_posts", '不是JSON'))
    print(execute_tool("unknown_tool", '{"keyword": "GORM"}'))
    print(execute_tool("get_post_detail", '{"post_id": 3}'))
    print(execute_tool("get_post_detail", '{"post_id": 999}'))
    print(execute_tool("get_post_detail", '{"post_id": "3"}'))

parameters = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "用于搜索帖子标题或正文的关键词"
        }
    },
    "required": ["keyword"]
}

search_tool = {
    "type": "function",
    "function": {
        "name": "search_posts",
        "description": (
            "按连续文本片段匹配社区帖子的标题或正文。"
            "不会自动分词，也不支持把空格分隔的多个词理解为同时匹配，多个关键词应独立搜索"
            "无同义词匹配，搜索关键词时必须精确"
            "优先使用问题中的明确名称或简短关键短语；已有相关候选时，优先读正文"
            "返回第一页最多5篇帖子的ID和标题，以及总数和分页信息,想要读取正文需要使用详情工具。"
            ),
        "parameters": parameters
    }
}

detail_tool = {
    "type": "function",
    "function": {
        "name": "fetch_post_detail",
        "description": "根据帖子 ID 获取完整帖子内容，可使用搜索结果中的 ID。",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "需要读取的帖子 ID"
                }
            },
            "required": ["post_id"]
        }
    }
}
