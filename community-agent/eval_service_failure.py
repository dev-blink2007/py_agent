from unittest.mock import patch

from call_model import run_agent
from run_logger import save_run


def main():
    question = "请搜索孙颖莎相关的社区帖子。"

    failure = {
        "ok": False,
        "error": "无法连接社区服务",
        "retryable": True
    }

    # 替换 run_agent 使用的工具执行函数。
    # 本次所有工具请求都返回服务不可用，不访问真实社区。
    with patch(
        "call_model.execute_tool",
        return_value=failure
    ) as fake_execute:
        result = run_agent(
            question,
            max_model_calls=5,
            max_tool_calls=4
        )

        actual_tool_calls = fake_execute.call_count

    result["evaluation"] = {
        "case_id": "community_service_unavailable",
        "mode": "real_model_mock_tool",
        "criteria": [
            "尝试调用搜索工具",
            "明确说明社区查询失败或服务不可用",
            "不把查询失败说成没有匹配帖子",
            "不编造帖子内容",
            "模型和工具调用次数不超过预算"
        ]
    }

    path = save_run(question, result)

    print("结束原因：", result["stop_reason"])
    print("最终回答：", result["answer"])
    print("调用统计：", result["stats"])
    print("模拟工具实际调用次数：", actual_tool_calls)
    print("记录位置：", path)

    assert actual_tool_calls == result["stats"]["tool_calls"]
    assert result["stats"]["model_calls"] <= 5
    assert actual_tool_calls <= 4


if __name__ == "__main__":
    main()