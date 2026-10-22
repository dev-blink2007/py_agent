from text_chunking import split_text

def build_index(model, posts):
    documents = []
    chunks = []

    for post in posts:
        content = post["content"]

        if not content.strip():
            continue

        documents.append({
            "id": post["id"],
            "title": post["title"],
            "content": content,
        })

        parts = split_text(
            content,
            chunk_size=200,
            overlap=40,
        )

        for part in parts:
            # 按字符切分不保证 Token 数一定符合要求，
            # 所以每个片段仍然要检查。
            token_count = len(
                model.tokenizer(
                    part["content"],
                    truncation=False,
                    add_special_tokens=True,
                )["input_ids"]
            )

            if token_count > model.max_seq_length:
                raise ValueError(
                    f"帖子 {post['id']} 的片段仍超过模型输入上限，"
                    "需要调整分块策略"
                )

            chunks.append({
                "post_id": post["id"],
                "title": post["title"],
                "start": part["start"],
                "end": part["end"],
                "content": part["content"],
            })

    if not chunks:
        return {
            "documents": [],
            "chunks": [],
            "vectors": None,
        }

    vectors = model.encode(
        [chunk["content"] for chunk in chunks],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return {
        "documents": documents,
        "chunks": chunks,
        "vectors": vectors,
    }

def search_index(model, index, query, top_k=3):
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "error": "查询内容必须是非空字符串",
        }

    if type(top_k) is not int or top_k <= 0:
        return {
            "ok": False,
            "error": "top_k 必须是正整数",
        }

    chunks = index["chunks"]

    if not chunks:
        return {
            "ok": True,
            "data": {"posts": []},
        }

    instruction = "为这个句子生成表示以用于检索相关文章："

    query_vector = model.encode(
        instruction + query.strip(),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    scores = index["vectors"] @ query_vector

    # 先排列全部片段，再收集 top_k 篇不同帖子。
    # 不能在这里先取 [:top_k]。
    ranked_indices = scores.argsort()[::-1]

    ranked_chunks = []

    for position in ranked_indices:
        chunk = chunks[position]

        ranked_chunks.append({
            **chunk,
            "score": float(scores[position]),
        })

    candidates = select_unique_posts(
        ranked_chunks,
        top_k=top_k,
    )

    return {
        "ok": True,
        "data": {
            "posts": candidates,
        },
    }

def select_unique_posts(ranked_chunks, top_k=3):
    """
    ranked_chunks 已经按分数从高到低排列。
    每篇帖子保留第一个命中的片段，即最高分片段。
    """
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k 必须是正整数")

    candidates = []
    seen_post_ids = set()

    for chunk in ranked_chunks:
        post_id = chunk["post_id"]

        # TODO 1：
        if post_id in seen_post_ids:
            continue
        else:
            seen_post_ids.add(post_id)

        candidates.append({
            "id": post_id,
            "title": chunk["title"],
            "score": float(chunk["score"]),
            "matched_chunk": chunk["content"],
        })

        # TODO 2：
        if len(seen_post_ids) == top_k:
            break

    return candidates