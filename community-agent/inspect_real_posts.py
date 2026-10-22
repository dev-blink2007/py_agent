import json
import urllib.parse
import urllib.request
from pathlib import Path

from sentence_transformers import SentenceTransformer


BASE_URL = "http://127.0.0.1:8080"
MODEL_DIR = (
    Path(__file__).resolve().parent
    / "models"
    / "bge-small-zh-v1.5"
)


def fetch_all_posts():
    """分页读取真实帖子，仅保留检索需要的字段。"""
    posts = []
    seen_ids = set()
    page = 1

    while True:
        query = urllib.parse.urlencode({
            "page": page,
            "size": 10,
        })
        url = f"{BASE_URL}/api/posts?{query}"

        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        batch = payload["data"]

        if not batch:
            if len(posts) < payload["total"]:
                raise RuntimeError("分页提前返回空结果，帖子没有读取完整")
            break

        for post in batch:
            if post["id"] in seen_ids:
                raise RuntimeError(
                    "分页出现重复帖子，请在社区数据不变时重新运行"
                )

            seen_ids.add(post["id"])
            posts.append({
                "id": post["id"],
                "title": post["title"],
                "content": post["content"],
            })

        if len(posts) >= payload["total"]:
            break

        page += 1

    return posts


def main():
    posts = fetch_all_posts()
    print("读取到的真实帖子数量：", len(posts))

    model = SentenceTransformer(
        str(MODEL_DIR),
        device="cpu",
        local_files_only=True,
    )

    limit = model.max_seq_length
    print("模型输入长度上限：", limit, "tokens")

    oversized_ids = []

    for post in posts:
        # 本次沿用“只编码正文”的实验方案。
        text = post["content"]

        encoded = model.tokenizer(
            text,
            truncation=False,
            add_special_tokens=True,
        )
        token_count = len(encoded["input_ids"])

        print(
            f"帖子 ID={post['id']} "
            f"标题={post['title']} "
            f"字符数={len(text)} "
            f"Token 数={token_count}"
        )

        if token_count > limit:
            oversized_ids.append(post["id"])

    print("超过输入长度上限的帖子：", oversized_ids)

    if not posts:
        print("社区没有帖子，暂不进行语义检索。")
        return

    if oversized_ids:
        print("存在超长正文，先处理长度问题，再进行本次实验。")
        return

    # 沿用前面的实验方案：只用正文生成向量。
    texts = [post["content"] for post in posts]

    post_vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    questions = [
        "哪位运动员获得过奥运会单打第二名？",
        "数据库连接没有释放，导致连接池耗尽，应该怎么处理？",
        "孙颖莎东京奥运会女单决赛的具体比分是多少？",
    ]

    instruction = "为这个句子生成表示以用于检索相关文章："

    for question in questions:
        query_vector = model.encode(
            instruction + question,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        scores = post_vectors @ query_vector
        ranked_indices = scores.argsort()[::-1][:3]

        print("\n" + "=" * 60)
        print("问题：", question)

        for rank, index in enumerate(ranked_indices, start=1):
            post = posts[index]

            print(
                f"{rank}. 帖子 ID={post['id']} "
                f"相似度={scores[index]:.4f} "
                f"标题={post['title']}"
            )
            print("正文：", post["content"])


if __name__ == "__main__":
    main()