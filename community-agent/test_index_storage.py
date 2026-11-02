import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from index_storage import save_index,load_index
from unittest.mock import patch


def test_load_index():
    # 准备一个只有一个帖子、一个片段的测试索引。
    # 向量只用 3 个数字：这里测试保存，不测试检索效果。
    index = {
        "version": "test-version-A",
        "documents": [],
        "chunks": [
            {
                "post_id": 5,
                "title": "测试帖子",
                "start": 0,
                "end": 4,
                "content": "第一段。",
            }
        ],
        "vectors": np.array([[0.1, 0.2, 0.3]], dtype=np.float32),
    }

    # 创建测试专用目录，退出 with 后自动清理。
    # 不会覆盖真实的 storage/retrieval_index.json。
    with TemporaryDirectory() as directory:
        target_path = Path(directory) / "index.json"

        # 执行被测试的函数。
        save_index(index, target_path)

        # 读回文件，检查实际保存的内容。
        with target_path.open("r", encoding="utf-8") as file:
            saved = json.load(file)

        assert saved["version"] == index["version"]
        assert saved["documents"] == index["documents"]
        assert saved["chunks"] == index["chunks"]
        assert saved["vectors"] == index["vectors"]

        result = load_index(target_path.with_name(target_path.name + ".tmp"))
    

def test_replace_failure_keeps_old_file():
    index = {
        "version": "test-version-A",
        "documents": [
            {"id": 5, "title": "测试帖子", "content": "第一段。第二段。"}
        ],
        "chunks": [
            {
                "post_id": 5,
                "title": "测试帖子",
                "start": 0,
                "end": 4,
                "content": "第一段。",
            }
        ],
        "vectors": np.array([[0.1, 0.2, 0.3]], dtype=np.float32),
    }
    new_index = {
            "version": "test-version-B",
            "documents": [],
            "chunks": [],
            "vectors": None,
    }
    with TemporaryDirectory() as directory:
            target_path = Path(directory) / "index.json"
            save_index(index, target_path)
            with patch(
                "index_storage.os.replace",
                side_effect=OSError("模拟替换文件失败"),
            ):
                try:
                    save_index(new_index, target_path)
                except OSError as error:
                    assert "模拟替换文件失败" in str(error)
                else:
                    raise AssertionError("预期保存失败，但函数没有抛出 OSError")
            with target_path.open("r", encoding="utf-8") as file:                        
                        saved = json.load(file)
            assert saved["version"] == index["version"]
            assert saved["documents"] == index["documents"]
            assert saved["chunks"] == index["chunks"]
            assert saved["vectors"] == index["vectors"].tolist()
            assert new_index["version"] == "test-version-B"
    print("通过：索引内容正确保存，原向量类型保持不变")



if __name__ == "__main__":
    test_load_index()
