import json
import os
from pathlib import Path
import numpy as np


INDEX_PATH = (
    Path(__file__).resolve().parent / "storage" / "retrieval_index.json" #.parent取所在目录（去掉脚本文件名）
)


def save_index(index, target_path=INDEX_PATH):
    target_path = Path(target_path)

    # 确保父目录存在。
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 当前单进程的刷新锁保证不会同时进行两次保存。
    temporary_path = target_path.with_name(target_path.name + ".tmp")

    if index["vectors"] is None:
        payload = {
            "version": index["version"],
            "documents": [],
            "chunks": [],
            "vectors": None 
        } 
    else:
        payload = {
            "version": index["version"],
            "documents": index["documents"],
            "chunks": index["chunks"],
            "vectors": index["vectors"].tolist() 
        }
    
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, allow_nan=False)

    os.replace(temporary_path, target_path)

def load_index(target_path = INDEX_PATH):
    target_path = Path(target_path)
    try:
        with target_path.open("r",encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError:
        return None
    if not isinstance(payload, dict):
        raise ValueError("索引文件的最外层必须是对象")
    required_fields = ("version", "documents", "chunks", "vectors")

    for field in required_fields:
        if field not in payload:
            raise ValueError(f"索引文件缺少字段：{field}")
    
    version = payload["version"]

    if not isinstance(version, str):
        raise ValueError("索引版本必须是字符串")
    if not version.strip():
        raise ValueError("索引版本不能为空")
    
    if not isinstance(payload["documents"], list):
            raise ValueError("documents必须是列表")
    
    if not isinstance(payload["chunks"],list):
            raise ValueError("chunks必须是列表")

    if not payload["documents"] and not payload["chunks"]:
        if payload["vectors"] is None:
            return {
                "version":payload["version"],
                "documents":[],
                "chunks":[],
                "vectors":None
            }
        raise ValueError("空索引不符合要求")
    
    if not payload["documents"] or not payload["chunks"]:
        raise ValueError("空索引不符合要求")
    
    try:
        vectors = np.array(payload["vectors"], dtype=np.float32)
    except (TypeError, ValueError) as error:
        raise ValueError("vectors 必须能转换为数值数组") from error

    if vectors.ndim != 2:
        raise ValueError("数组应该是二维")
    
    if vectors.shape[0] != len(payload["chunks"]):
        raise ValueError("向量行数应等于片段数")
    return {
        "version":payload["version"],
        "documents":payload["documents"],
        "chunks":payload["chunks"],
        "vectors":vectors
    }
    