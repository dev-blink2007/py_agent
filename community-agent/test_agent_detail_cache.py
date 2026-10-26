import json
from unittest.mock import patch

from call_model import run_agent


def tool_call(call_id, name, arguments):
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


def model_reply(tool_calls=None, content=None):
    message = {
        "role": "assistant",
        "content": content,
    }

    if tool_calls:
        message["tool_calls"] = tool_calls

    return {"message": message, "usage": None}


def main():
    responses = [
        model_reply([
            tool_call("seed", "search_posts", {"keyword": "连接池"}),
        ]),
        model_reply([
            tool_call("first", "fetch_post_detail", {"post_id": 5}),
            tool_call("second", "fetch_post_detail", {"post_id": 5}),
        ]),
        model_reply(content="测试结束"),
    ]

    def fake_execute(name, arguments_text):
        if name == "search_posts":
            return {
                "ok": True,
                "data": {
                    "posts": [{"id": 5, "title": "测试帖子"}],
                },
            }

        if name == "fetch_post_detail":
            return {
                "ok": True,
                "data": {
                    "id": 5,
                    "title": "测试帖子",
                    "content": "测试正文",
                },
            }

        raise AssertionError(f"出现意外工具：{name}")

    with (
        patch(
            "call_model.call_model",
            side_effect=responses,
        ) as model,
        patch(
            "call_model.execute_tool",
            side_effect=fake_execute,
        ) as executor,
    ):
        result = run_agent(
            "测试同一次运行内的详情缓存",
            max_model_calls=3,
            max_tool_calls=3,
        )

    # 搜索一次、详情请求两次，预算一共消耗三次。
    stats = result["stats"]
    assert stats["tool_calls"] == 3
    assert stats["detail_calls"] == 2
    assert stats["detail_cache_hits"] == 1
    assert stats["detail_backend_calls"] == 1

    # 执行器只收到一次搜索和一次详情查询。
    assert [call.args[0] for call in executor.call_args_list] == [
        "search_posts",
        "fetch_post_detail",
    ]

    detail_records = [
        record for record in result["tool_records"]
        if record["name"] == "fetch_post_detail"
    ]
    assert [record["cache_hit"] for record in detail_records] == [
        False,
        True,
    ]

    # 第三轮模型必须收到两个独立请求各自的反馈。
    messages = model.call_args_list[2].args[0]
    feedback = {
        message["tool_call_id"]: json.loads(message["content"])
        for message in messages
        if message["role"] == "tool"
    }

    assert feedback["first"] == feedback["second"]
    assert feedback["first"]["data"]["id"] == 5
    assert result["stop_reason"] == "completed"

    print("通过：重复详情请求复用缓存，预算和工具反馈保持正确。")
    print("统计：", stats)


if __name__ == "__main__":
    main()