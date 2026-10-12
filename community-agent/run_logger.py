import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


def save_run(question, result):
    run_id = uuid4().hex

    # 将记录保存到本文件旁边的 runs 文件夹。
    runs_dir = Path(__file__).resolve().parent / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "run_id": run_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "result": result
    }

    file_path = runs_dir / f"{run_id}.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)

    return str(file_path)