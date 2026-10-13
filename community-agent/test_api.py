from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app

with patch.dict("os.environ", {"DEEPSEEK_API_KEY": ""}):
    try:
        with TestClient(app):
            pass
    except RuntimeError as error:
        assert "DEEPSEEK_API_KEY" in str(error)
        print("通过：缺少 API Key 时拒绝启动")
    else:
        raise AssertionError(
            "缺少 API Key 时，服务不应该启动成功"
        )

def main():
    fake_result = {
        "answer": "测试回答",
        "stop_reason": "completed",
        "error": None,
        "stats": {
            "model_calls": 1,
            "search_calls": 0,
            "detail_calls": 0,
            "tool_calls": 0
        },
        "tool_records": [],
        "blocked_tool_calls": []
    }

    with (
        patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}),
        TestClient(app) as client
    ):     #创建一个 TestClient 实例,把这个实例赋值给变量名 client,并用with在结束后可以自动做清理工作 
        with (
            patch("api.run_agent", return_value=fake_result) as mock_agent,
            patch("api.save_run", return_value="runs/test_run.json") as mock_save
        ):
            # 1. 非法请求应该被拦截。
            invalid_bodies = [
                {},                       # 缺少 question
                {"question": ""},         # 空字符串
                {"question": "   "},      # 纯空白
                {"question": 123},         # 类型错误
                {"question": "问" * 2001}  # 超出长度限制
            ]

            for body in invalid_bodies:
                response = client.post("/agent/run", json=body)
                assert response.status_code == 422, (
                    f"预期 422，实际为 {response.status_code}"
                )

            mock_agent.assert_not_called()     #一次都没调用
            mock_save.assert_not_called()
            print("通过：非法请求被拦截，未执行 Agent 或保存记录")

            # 2. 合法请求应该执行，并去掉问题两端的空白。
            response = client.post(
                "/agent/run",
                json={"question": "  测试问题  "}
            )

            assert response.status_code == 200

            data = response.json()
            assert data["run_id"] == "test_run"
            assert data["answer"] == "测试回答"
            assert data["stop_reason"] == "completed"
            assert data["stats"] == fake_result["stats"]
            assert data["error"] is None

            mock_agent.assert_called_once_with("测试问题")           #只调用了一次
            mock_save.assert_called_once_with("测试问题", fake_result)
            print("通过：合法请求正确执行、传递保存数据并返回结果")

            #3.返回502模型调用失败
            # 清空之前的调用次数，单独检查这个场景。
            mock_agent.reset_mock()
            mock_save.reset_mock()

            failed_result = fake_result.copy()
            failed_result["answer"] = "模型服务请求失败，任务尚未完成。"
            failed_result["stop_reason"] = "model_error"
            failed_result["error"] = {
                "type": "model_connection_error",
                "message": "无法连接模型服务"
            }

            mock_agent.return_value = failed_result
            mock_save.return_value = "runs/model_error_test.json"

            response = client.post(
                "/agent/run",
                json={"question": "测试模型故障"}
            )

            assert response.status_code == 502

            data = response.json()
            assert data["stop_reason"] == "model_error"
            assert data["error"]["type"] == "model_connection_error"
            assert data["run_id"] == "model_error_test"

            mock_agent.assert_called_once_with("测试模型故障")
            mock_save.assert_called_once_with(
                "测试模型故障",
                failed_result
            )

            print("通过：模型失败返回 502，并传递失败记录给保存函数")

    print("接口测试全部通过")


if __name__ == "__main__":
    main()