from sentence_transformers import SentenceTransformer


# 实验资料，不是社区数据库中的帖子 ID。
docs = [
    {
        "id": "P1",
        "title": "孙颖莎",
        "content": (
            "2021年，获东京奥运会乒乓球女单亚军、女团冠军。"
        )
    },
    {
        "id": "P2",
        "title": "模拟资料：世乒赛成绩",
        "content": "选手甲获得世界乒乓球锦标赛女子单打亚军。"
    },
    {
        "id": "P3",
        "title": "模拟资料：奥运会团体成绩",
        "content": "选手乙获得东京奥运会乒乓球女子团体冠军。"
    },
    {
        "id": "P4",
        "title": "模拟资料：奥运会单打成绩",
        "content": "选手丙获得东京奥运会乒乓球男子单打冠军。"
    },
    {
        "id": "P5",
        "title": "GORM 连接池配置",
        "content": "记录数据库最大打开连接数和最大空闲连接数的配置。"
    }
]

queries = [
    "奥运会单打第二名",
    "GORM",
    "孙颖莎东京奥运会女单决赛具体比分"
]

model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5",
    device="cpu"
)

texts = [
    f"{doc['title']}\n{doc['content']}"
    for doc in docs
]

# 每篇资料转换为一个向量，整个实验只需计算一次。
doc_vectors = model.encode(
    texts,
    normalize_embeddings=True,
    convert_to_numpy=True
)

print("资料向量形状：", doc_vectors.shape)

instruction = "为这个句子生成表示以用于检索相关文章："

for query in queries:
    print("\n问题：", query)

    # 对照组：直接使用完整问题进行连续文本匹配。
    literal_hits = [
        doc["id"]
        for doc in docs
        if query in doc["title"] or query in doc["content"]
    ]
    print("连续文本匹配：", literal_hits)

    query_vector = model.encode(
        instruction + query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    # 向量已归一化，此处点积得到余弦相似度。
    scores = doc_vectors @ query_vector

    # 分数从高到低排序，取前 3 篇。
    top_indices = scores.argsort()[::-1][:3]

    print("语义检索前 3 篇：")
    for index in top_indices:
        doc = docs[index]
        print(
            doc["id"],
            f"相似度={float(scores[index]):.4f}",
            doc["title"]
        )