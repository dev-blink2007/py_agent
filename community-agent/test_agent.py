from unittest.mock import patch
from call_model import run_agent
from run_logger import save_run
import urllib.error

# 模拟模型直接回答。
answer_reply = {
    "role": "assistant",
    "content": "测试回答"
}

# 模拟模型请求搜索。
tool_reply = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "test_call_1",
            "type": "function",
            "function": {
                "name": "search_posts",
                "arguments": '{"keyword": "测试"}'
            }
        }
    ]
}

# 1. 正常完成
with patch("call_model.call_model", return_value=answer_reply):
    result = run_agent("测试问题")
    assert result["stop_reason"] == "completed"
    assert result["answer"] == "测试回答"
    print("正常完成：", result)

# 2. 工具预算不足：预算为 0，因此工具不应执行。
with patch("call_model.call_model", return_value=tool_reply):
    with patch("call_model.execute_tool") as fake_tool:
        result = run_agent("测试问题", max_tool_calls=0)
        assert result["stop_reason"] == "tool_budget_exceeded"
        assert result["stats"]["tool_calls"] == 0
        assert result["tool_records"] == []
        assert "工具调用预算不足" in result["answer"]
        assert len(result["blocked_tool_calls"]) == 1
        assert result["blocked_tool_calls"][0]["function"]["name"]== "search_posts"
        print("工具预算不足：", result)
        print("实际执行工具次数：", fake_tool.call_count)

# 3. 模型轮数耗尽：只允许一轮，该轮请求了工具，还没生成回答。
with patch("call_model.call_model", return_value=tool_reply):
    with patch(
        "call_model.execute_tool",
        return_value={"ok": True, "data": []}
    ):
        assert result["stop_reason"] == "max_model_calls"
        assert "模型调用轮数上限" in result["answer"]
        result = run_agent("测试问题", max_model_calls=1)
        print("轮数耗尽：", result)

        saved_path = save_run("测试问题", result)
        print("记录已保存：", saved_path)

with patch("call_model.call_model",side_effect=urllib.error.URLError("模拟断网")):
    result = run_agent("测试模型断网")

    assert result["stop_reason"] == "model_error", "断网时应返回 model_error"
    assert "模型服务请求失败" in result["answer"]
    assert result["error"] is not None
    assert result["error"]["type"] == "model_connection_error"
    assert result["stats"]["model_calls"] == 1
    assert result["stats"]["tool_calls"] == 0
    assert result["tool_records"] == []

    print("模型断网测试通过")

    print(result)
    saved_path = save_run("测试模型断网", result)
    print("记录已保存：", saved_path)