from retrieval_client import fetch_semantic_posts
from retrieval_eval_cases import RETRIEVAL_CASES


def is_hit(candidate_ids, evidence_ids, k):
    # TODO：
    # 取 candidate_ids 的前 k 个 ID。
    # 判断它们与 evidence_ids 是否有交集。
    # 返回 True 或 False。
    order = candidate_ids[:k]
    for id in evidence_ids:
        if id in order:
            return True
    return False


def main():
    # 先检查指标函数，避免检索结果正确但统计代码写错。
    assert is_hit([7, 5], [5], 1) is False
    assert is_hit([7, 5], [5], 2) is True
    assert is_hit([], [5], 2) is False
    assert is_hit([4, 1], [], 2) is False

    answerable_count = 0
    hit_at_1_count = 0
    hit_at_2_count = 0
    error_count = 0

    for case in RETRIEVAL_CASES:
        evidence_ids = case["evidence_ids"]
        answerable = bool(evidence_ids)

        if answerable:
            answerable_count += 1

        print("\n案例：", case["id"])
        print("问题：", case["query"])
        print("回答依据 ID：", evidence_ids)

        result = fetch_semantic_posts(case["query"])

        if result.get("ok") is not True:
            error_count += 1
            print("检索执行失败：", result)

            # 有答案案例执行失败时，仍保留在分母中，
            # 本次没有成功召回依据，不能跳过以抬高指标。
            continue

        # 客户端固定请求前三篇。
        # 本次只评估前两篇，不改变检索服务配置。
        candidates = result["data"]["posts"][:2]
        candidate_ids = [post["id"] for post in candidates]

        print("候选 ID：", candidate_ids)

        if answerable:
            hit_1 = is_hit(candidate_ids, evidence_ids, 1)
            hit_2 = is_hit(candidate_ids, evidence_ids, 2)

            hit_at_1_count += int(hit_1)
            hit_at_2_count += int(hit_2)

            print("Hit@1：", hit_1)
            print("Hit@2：", hit_2)
        else:
            print("无答案案例：不计入 Hit 指标，单独检查返回内容。")

        for post in candidates:
            print(
                f"帖子 {post['id']} "
                f"分数={post['score']:.4f}"
            )
            print("命中片段：", post.get("matched_chunk", ""))

    print("\n评测汇总")
    print("有答案案例数：", answerable_count)
    print("全部案例中的请求失败数：", error_count)

    if answerable_count:
        print(
            f"Hit@1：{hit_at_1_count}/{answerable_count}"
            f" = {hit_at_1_count / answerable_count:.1%}"
        )
        print(
            f"Hit@2：{hit_at_2_count}/{answerable_count}"
            f" = {hit_at_2_count / answerable_count:.1%}"
        )


if __name__ == "__main__":
    main()