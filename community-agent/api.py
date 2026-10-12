from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from call_model import run_agent
from run_logger import save_run
from fastapi.responses import JSONResponse


app = FastAPI(title="社区 Agent 服务") #new 一个 FastAPI 对象，命名（赋值）为 app


class AgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "community-agent"
    }


@app.post(
    "/agent/run",
    responses={502: {"description": "模型服务请求失败"}} #作用是/docs 里显示 502 的说明，和每次运行返回的状态码无关，装饰器里的 responses 将 502 的说明加入接口文档。
)
def agent_run(request: AgentRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="问题不能为空或只有空白字符"
        )

    result = run_agent(question)

    # 保存完整运行记录，包括工具调用过程。
    path = save_run(question, result)

    # 文件名不含 .json 的部分，就是现有保存函数生成的运行 ID。
    run_id = Path(path).stem

    response_body = {
        "run_id": run_id,
        "answer": result["answer"],
        "stop_reason": result["stop_reason"],
        "stats": result["stats"],
        "error": result["error"]
    }

    if result["stop_reason"] == "model_error":
        status_code = 502
    else:
        status_code = 200

    return JSONResponse(    #JSONResponse 允许我们同时指定 JSON 正文和 HTTP 状态码
        status_code=status_code,
        content=response_body
    )