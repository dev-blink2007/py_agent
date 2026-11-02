import asyncio
from unittest.mock import patch

from fastapi import FastAPI
from retrieval_api import lifespan


async def test_invalid_index_rebuilds():
    app = FastAPI()

    # 只测试启动流程，不需要加载真实向量模型。
    fake_model = object()

    rebuilt_index = {
        "documents": [],
        "chunks": [],
        "vectors": None,
    }

    with (
        patch(
            "retrieval_api.SentenceTransformer",
            return_value=fake_model,
        ),
        patch(
            "retrieval_api.load_index",
            side_effect=ValueError("模拟索引文件损坏"),
        ),
        patch(
            "retrieval_api.fetch_all_posts",
            return_value=[],
        ) as fetch_mock,
        patch(
            "retrieval_api.build_index",
            return_value=rebuilt_index,
        ) as build_mock,
        patch(
            "retrieval_api.save_index",
        ) as save_mock,
    ):
        async with lifespan(app):
            # TODO：在这里补充下面列出的检查。
            fetch_mock.assert_called_once()
            build_mock.assert_called_once()
            save_mock.assert_called_once()
            app.state.retrieval_index["version"] == app.state.save_version


    print("通过：索引文件无效时，启动流程重建并保存新索引")


if __name__ == "__main__":
    asyncio.run(test_invalid_index_rebuilds())