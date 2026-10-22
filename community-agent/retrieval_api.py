from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sentence_transformers import SentenceTransformer

from inspect_real_posts import fetch_all_posts
from semantic_retrieval import build_index, search_index

import logging
from threading import Lock
from uuid import uuid4

MODEL_DIR = (
    Path(__file__).resolve().parent
    / "models"
    / "bge-small-zh-v1.5"
)


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=500,
        strict=True,
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=5,
        strict=True,
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("查询内容不能为空")

        return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("开始加载检索模型……")

    model = SentenceTransformer(
        str(MODEL_DIR),
        device="cpu",
        local_files_only=True,
    )

    print("开始读取社区帖子并建立索引……")

    posts = fetch_all_posts()
    index = build_index(model, posts)
    index["version"] = uuid4().hex
    app.state.refresh_lock = Lock()

    # 保存到当前应用实例，供后面的请求复用。
    app.state.retrieval_model = model
    app.state.retrieval_index = index

    print(
        "检索服务准备完成，已索引帖子数：",
        len(index["documents"]),
    )

    yield      #yield 前面：启动准备工作。准备成功后，服务才开始接收请求

    # 服务退出时释放应用持有的引用。
    del app.state.retrieval_index
    del app.state.retrieval_model


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health(request: Request):
    index = request.app.state.retrieval_index

    return {
        "status": "ok",
        "service": "community-retrieval",
        "indexed_posts": len(index["documents"]),
        "index_version": index["version"],
    }

@app.post("/search")
def search(body: SearchRequest, request: Request):
    model = request.app.state.retrieval_model
    index = request.app.state.retrieval_index

    print(
        "收到语义查询：",
        body.query,
        "top_k：",
        body.top_k,
    )

    return search_index(
        model,
        index,
        body.query,
        top_k=body.top_k,
    )

@app.post("/index/refresh")
def refresh_index(request: Request):
    state = request.app.state

    # 同一时间只允许一个刷新任务。
    # 已有刷新任务时，立即拒绝，不排队等待。
    if not state.refresh_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="已有索引刷新任务正在执行",
        )

    try:
        model = state.retrieval_model

        # 准备阶段：读取资料、建立新索引。
        # 此时正在使用的旧索引仍然保留。
        posts = fetch_all_posts()
        new_index = build_index(model, posts)
        new_index["version"] = uuid4().hex

        # TODO：提交阶段。
        # 用 new_index 替换应用正在使用的 retrieval_index。
        # 请补充一行代码。
        state.retrieval_index = new_index

        return {
            "ok": True,
            "data": {
                "indexed_posts": len(new_index["documents"]),
                "index_version": new_index["version"],
            },
        }

    except Exception:
        logging.exception("索引刷新失败，保留旧索引")

        raise HTTPException(
            status_code=503,
            detail="索引刷新失败，旧索引仍保留",
        )

    finally:
        state.refresh_lock.release()