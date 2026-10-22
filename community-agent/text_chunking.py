def split_text(text, chunk_size=200, overlap=40):
    if not isinstance(text, str):
        raise ValueError("text 必须是字符串")

    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError("chunk_size 必须是正整数")

    if (
        type(overlap) is not int
        or overlap < 0
        or overlap >= chunk_size
    ):
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")

    if not text.strip():
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunks.append({
            "start": start,
            "end": end,
            "content": text[start:end],
        })

        # 已覆盖到正文末尾，不再制造一个重复的尾部片段。
        if end == len(text):
            break

        # TODO：计算下一段的起点。
        # 要让下一段与当前段重叠 overlap 个字符。
        start = end - overlap

    return chunks