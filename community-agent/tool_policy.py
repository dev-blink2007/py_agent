import json


ALLOWED_TOOLS = {"search_posts", "fetch_post_detail"}


def is_priority_detail(tool_call, discovered_post_ids):
    """判断：是否是读取已搜索到帖子的详情请求。"""
    function = tool_call["function"]

    if function["name"] != "fetch_post_detail":
        return False

    try:
        arguments = json.loads(function["arguments"])
    except (json.JSONDecodeError, TypeError):
        return False

    if not isinstance(arguments, dict):
        return False

    post_id = arguments.get("post_id")

    return (
        type(post_id) is int
        and post_id > 0
        and post_id in discovered_post_ids
    )


def plan_tool_batch(tool_calls, remaining_budget, discovered_post_ids):
    if type(remaining_budget) is not int or remaining_budget < 0:
        raise ValueError("remaining_budget 必须是非负整数")

    priority = []
    normal = []
    blocked = []

    for tool_call in tool_calls:
        name = tool_call["function"]["name"]

        if name not in ALLOWED_TOOLS:
            blocked.append({
                "tool_call": tool_call,
                "reason": "unknown_tool"
            })
            continue

        if is_priority_detail(tool_call,discovered_post_ids):
            priority.append(tool_call)
        else:
            normal.append(tool_call)

    ordered = priority + normal

    selected = ordered[:remaining_budget]

    for tool_call in ordered[remaining_budget:]:
        blocked.append(
            {
                "tool_call": tool_call,
                "reason": "tool_budget_exceeded"
            }
        )

    return {
        "selected": selected,
        "blocked": blocked
    }