import json
from unittest.mock import patch

from call_model import run_agent


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

if __name__ == "__main__":
    test_model_returns_after_deadline()