import copy
import json
from unittest.mock import patch

from call_model import run_agent


def make_call(call_id, name, arguments):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments, ensure_ascii=False)
        }
    }


def model_result(message):
    return {
        "message": message,
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }


responses = [
    # 第一轮：先搜索，建立“发现过帖子 4”的依据。
    model_result({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            make_call("seed", "search_posts", {"keyword": "孙颖莎"})
        ]
    }),

    # 第二轮：剩余预算 2，但模型请求了 3 个工具。
    model_result({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            make_call("A", "search_posts", {"keyword": "陈梦"}),
            make_call("B", "fetch_post_detail", {"post_id": 4}),
            make_call("C", "search_posts", {"keyword": "奥运会"})
        ]
    }),

    # 第三轮：模拟模型给出最终回答。
    model_result({
        "role": "assistant",
        "content": "已读取帖子 ID 4，其正文未提供具体比分。"
    })
]

snapshots = []
executions = []


def fake_model(messages, tools):
    # 必须复制：后续 Agent 会继续修改同一个 messages 列表。
    snapshots.append(copy.deepcopy(messages))
    return responses[len(snapshots) - 1]


def fake_execute(tool_name, arguments_text):
    arguments = json.loads(arguments_text)
    executions.append((tool_name, arguments))

    if tool_name == "fetch_post_detail":
        return {
            "ok": True,
            "data": {
                "id": 4,
                "title": "孙颖莎",
                "content": "2021 年获得东京奥运会女单亚军。"
            }
        }

    posts = (
        [{"id": 4, "title": "孙颖莎"}]
        if arguments["keyword"] == "孙颖莎"
        else []
    )

    return {
        "ok": True,
        "data": {
            "posts": posts,
            "total": len(posts),
            "page": 1,
            "size": 5
        }
    }


with (
    patch("call_model.call_model", side_effect=fake_model),
    patch("call_model.execute_tool", side_effect=fake_execute)
):
    result = run_agent(
        "根据社区帖子查询孙颖莎的决赛比分",
        max_model_calls=3,
        max_tool_calls=3
    )


# 1. 第一轮执行搜索；第二轮按 B、A 的顺序执行。
assert executions == [
    ("search_posts", {"keyword": "孙颖莎"}),
    ("fetch_post_detail", {"post_id": 4}),
    ("search_posts", {"keyword": "陈梦"})
]

# 2. C 没执行，总次数没有超过预算。
assert result["stats"]["tool_calls"] == 3
assert result["stats"]["search_calls"] == 2
assert result["stats"]["detail_calls"] == 1
assert len(result["tool_records"]) == 3

assert len(result["blocked_tool_calls"]) == 1
blocked = result["blocked_tool_calls"][0]
assert blocked["id"] == "C"
assert blocked["reason"] == "tool_budget_exceeded"

# 3. 第三轮模型调用前，A、B、C 均有对应结果。
batch_messages = [
    message
    for message in snapshots[2]
    if message["role"] == "tool"
    and message["tool_call_id"] in {"A", "B", "C"}
]

assert [m["tool_call_id"] for m in batch_messages] == ["A", "B", "C"]

feedback = {
    m["tool_call_id"]: json.loads(m["content"])
    for m in batch_messages
}

assert feedback["A"]["ok"] is True
assert feedback["B"]["data"]["id"] == 4
assert feedback["C"]["ok"] is False
assert feedback["C"]["code"] == "tool_budget_exceeded"

# 4. 拒绝部分请求后，仍能进入下一轮取得最终回答。
assert result["stop_reason"] == "completed"
assert result["stats"]["model_calls"] == 3
assert result["stats"]["total_tokens"] == 45
assert result["stats"]["usage_complete"] is True

print("部分执行、预算限制、结果回传、最终回答：全部通过")

responses = [
    model_result({
        "role":"assistant",
        "content":None,
        "tool_calls": [
            make_call("seed", "search_posts", {"keyword": "孙颖莎"})
        ]
    }),
    model_result({
        "role":"assistant",
        "content":"预算不足，尚未取得资料"
    })
]
snapshots = []
executions = []
with (
    patch("call_model.call_model", side_effect=fake_model) as mock_call_model,
    patch("call_model.execute_tool", side_effect=fake_execute) as mock_call_tool
):
    result = run_agent(
        "根据社区帖子查询孙颖莎的决赛比分",
        max_model_calls=3,
        max_tool_calls=0
    )
mock_call_tool.assert_not_called()
assert mock_call_model.call_count == 2
# 取出第二次调用时，传给模型的消息。
second_messages = snapshots[1]

# 找到对应 seed 请求的工具结果。
seed_results = [
    message
    for message in second_messages
    if message["role"] == "tool"
    and message["tool_call_id"] == "seed"
]

# 不仅要存在，还应该恰好有一条。
assert len(seed_results) == 1

# 工具结果的 content 是 JSON 字符串，需要解析。
tool_result = json.loads(seed_results[0]["content"])

assert tool_result["ok"] is False
assert tool_result["code"] == "tool_budget_exceeded"
assert tool_result["retryable"] is False

print("额外测试通过")