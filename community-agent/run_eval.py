from call_model import run_agent
from eval_cases import EVAL_CASES
from run_logger import save_run


def main():
    target_ids = {
        "rag_connection_fix",
        "rag_missing_configuration",
        "rag_missing_score",
    }
    for case in EVAL_CASES:
        if case["id"] not in target_ids:
            continue

        # 保留后面的运行、人工判断和保存代码。
        print("\n开始测试：", case["id"])
        print("问题：", case["question"])

        # 调用你已经写好的 Agent。
        result = run_agent(case["question"])

        # 在结果中附上题目编号和验收标准。
        result["evaluation"] = {
            "case_id": case["id"],
            "criteria": case["criteria"]
        }

        print("结束原因：", result["stop_reason"])
        print("最终回答：", result["answer"])
        print("调用统计：", result["stats"])
        print("未执行的工具请求：")
        for tool_call in result.get("blocked_tool_calls", []):
            print(
                tool_call["function"]["name"],
                tool_call["function"]["arguments"]
            )

        print("请按以下标准检查回答：")
        for criterion in case["criteria"]:
            print("-", criterion)

        while True:         #将用户反馈写入评测
            verdict = input("本案例是否通过？输入 pass 或 fail：").strip().lower()

            if verdict in ("pass", "fail"):
                break

            print("请输入 pass 或 fail。")

        note = input("请输入判断依据：").strip()

        result["evaluation"]["verdict"] = verdict
        result["evaluation"]["note"] = note

        # 使用你已经写好的函数保存文件。
        path = save_run(case["question"], result)

        print("人工评测结果：", verdict)
        print("判断依据：", note)
        print("记录位置：", path)


if __name__ == "__main__":
    main()