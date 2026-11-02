from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sentence_transformers import SentenceTransformer

from inspect_real_posts import fetch_all_posts
from semantic_retrieval import build_index, search_index
from index_storage import save_index,load_index

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

    try:
        index = load_index()

    except ValueError:
        logging.error("初始化索引文件无效，加载出错")
        index = None

    except Exception:
        raise 
    
    if index is None:
        posts = fetch_all_posts()
        index = build_index(model, posts)
        index["version"] = uuid4().hex
    
        try:
            save_index(index)
            app.state.save_version = index["version"]
        except OSError:
            logging.exception("启动索引已构建，但保存失败：index_version=%s",index["version"],)
            app.state.save_version = None
    else:
        app.state.save_version = index["version"]
    
    app.state.refresh_lock = Lock()
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
    del app.state.save_version


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health(request: Request):
    index = request.app.state.retrieval_index

    return {
        "status": "ok",
        "service": "community-retrieval",
        "indexed_posts": len(index["documents"]),
        "index_version": index["version"],
        "save_version": request.app.state.save_version
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
        try:
            model = state.retrieval_model

            # 准备阶段：读取资料、建立新索引。
            # 此时正在使用的旧索引仍然保留。
            posts = fetch_all_posts()
            new_index = build_index(model, posts)
            new_index["version"] = uuid4().hex
        except Exception:
            logging.exception("索引构建失败，旧索引仍保留")
            raise HTTPException(
                status_code=503,
                detail="索引构建失败，旧索引仍保留",
            )
        
        state.retrieval_index = new_index
        try:
            save_index(new_index)
            state.save_version = new_index["version"]
            return{
                "activated":True,
                "save_ok":True,
                "index_version":new_index["version"],
                "save_version":new_index["version"],
                "data": {
                    "indexed_posts": len(new_index["documents"]),
                    "index_chunks": len(new_index["chunks"])
                }
            }
        except OSError:
            logging.exception("索引已生效,但保存失败:index_version=%s,save_version=%s",new_index["version"],state.save_version,)
            return{
                "activated":True,
                "save_ok":False,
                "index_version":new_index["version"],
                "save_version":state.save_version,
                "data": {
                    "indexed_posts": len(new_index["documents"]),
                    "index_chunks": len(new_index["chunks"])
                }
            }

    finally:
        state.refresh_lock.release()