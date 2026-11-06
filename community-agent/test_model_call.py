import json
from unittest.mock import patch

from call_model import run_agent
from tools import execute_tool
import urllib.error
import urllib.request
from retrieval_client import fetch_semantic_posts


def test_model_returns_after_deadline():
    clock = {"now": 100.0}

    response = {
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "late_detail",
                    "type": "function",
                    "function": {
                        "name": "fetch_post_detail",
                        "arguments": json.dumps({"post_id": 5}),
                    },
                }
            ],
        },
        # 用具体数值验证：返回晚了，也不能漏记已消耗的用量。
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }

    def fake_clock():
        return clock["now"]

    def fake_model(messages, tools, timeout=120):
        # 模拟模型调用消耗了时间，返回时已经超过截止点。
        clock["now"] = 102.0
        return response

    with (
        patch("call_model.perf_counter", side_effect=fake_clock),
        patch(
            "call_model.call_model",
            side_effect=fake_model,
        ) as model_mock,
        patch(
            "call_model.execute_tool",
            side_effect=AssertionError("总预算耗尽后不应该执行工具"),
        ) as tool_mock,
    ):
        result = run_agent(
            question="测试问题",
            max_duration_seconds=1,
        )

    assert result["stop_reason"] == "deadline_exceeded"
    model_mock.assert_called_once()
    tool_mock.assert_not_called()

    assert result["stats"]["model_calls"] == 1
    assert result["stats"]["tool_calls"] == 0
    assert result["stats"]["prompt_tokens"] == 10
    assert result["stats"]["completion_tokens"] == 5
    assert result["stats"]["total_tokens"] == 15

    print("通过：模型返回时预算已耗尽，保留用量统计且不执行工具")

def client_tools_test():
    with patch(
        "tools.fetch_semantic_posts",
        return_value={"ok": True, "data": {"id": 5}},
    ) as fetch_mock:
        execute_tool(
            "semantic_search_posts",
            '{"query": "55"}',
            timeout=2,
        )

    fetch_mock.assert_called_once_with("55", timeout=2)
    print("测试通过")

def http_test():
    with patch(
        "retrieval_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("测试中阻止真实请求"),
    ) as urlopen_mock:
        fetch_semantic_posts("测试查询", timeout=2)

        assert urlopen_mock.call_count == 1, "urlopen 没有被调用"
        args, kwargs = urlopen_mock.call_args
        assert kwargs["timeout"] == 2
        request = args[0]
        assert isinstance(request, urllib.request.Request)
        print("测试通过")

def test_model_returns_after_tool_deadline():
    clock = {"now":100.0}
    def fake_clock():
        return clock["now"]
    response = [{
        "message": {
            "role": "assistant",
            "content": "第一轮回答",
            "tool_calls": [
                {
                    "id": "search_posts_first",
                    "type": "function",
                    "function": {
                        "name": "search_posts",
                        "arguments": json.dumps({"keyword": "测试关键词"}),
                    },
                }
            ],
        },
        # 用具体数值验证：返回晚了，也不能漏记已消耗的用量。
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
    },
    {
        "message": {
            "role": "assistant",
            "content": "第二轮回答",
            "tool_calls": [
                {
                    "id": "first",
                    "type": "function",
                    "function": {
                        "name": "fetch_post_detail",
                        "arguments": json.dumps({"post_id": 5}),
                    },
                },
                {
                    "id": "second",
                    "type": "function",
                    "function": {
                        "name": "fetch_post_detail",
                        "arguments": json.dumps({"post_id": 5}),
                    },
                },
            ],
        },
        # 用具体数值验证：返回晚了，也不能漏记已消耗的用量。
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    ]
    def fack_post_list(keyword,timeout=120):
        clock["now"] = 117
        return {
            "ok": True,
            "data": {
                "posts": [{
                    "id":5,
                    "title":"测试标题"
                }],
                "total": 1,
                "page": 1,
                "size": 1
            }
        }
    def fack_post_detail(post_id,timeout=120):
        clock["now"] = 120
        return {
            "ok": True,
            "data": {"id": post_id, "title": "测试标题", "content": "测试正文"},
        }

    with(
        patch("call_model.perf_counter", side_effect=fake_clock),
        patch("tools.fetch_post_list",side_effect = fack_post_list) ,
        patch("tools.fetch_post_detail",side_effect = fack_post_detail) as detail_mock,
        patch("call_model.call_model",side_effect = response) as model_mock
    ):
        result = run_agent(question="测试问题",max_duration_seconds=20)
        detail_mock.assert_called_once_with(5, timeout=3)

        assert result["stop_reason"] == "deadline_exceeded"
        assert model_mock.call_count == 2
        assert result["stats"]["tool_calls"] == 2
        assert result["stats"]["detail_cache_hits"] == 0

        records = result["tool_records"]
        assert [r["tool_call_id"] for r in records] == ["search_posts_first", "first"]
        assert records[1]["result"]["data"]["content"] == "测试正文"

        blocked = result["blocked_tool_calls"]
        assert [(r["id"], r["reason"]) for r in blocked] == [
            ("second", "deadline_exceeded")
        ]
    print("测试通过")

if __name__ == "__main__":
    test_model_returns_after_tool_deadline()