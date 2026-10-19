"""usmile AI 护齿助手 Demo 的 HTTP 接口（FastAPI）。

个人作品集项目，非 usmile 官方，未上线。接口说明见 docs/API.md。
启动：.venv/bin/uvicorn src.api:app --port 8000   （交互文档：http://127.0.0.1:8000/docs）
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.core import service

app = FastAPI(title="usmile AI 护齿助手 Demo API（个人作品集，非官方，未上线）", version="0.1.0")


class QuizAnswers(BaseModel):
    q1: str | None = Field(None, description="预算（必答），取值见 GET /quiz")
    q2: list[str] = Field(default_factory=list, description="牙齿情况，多选")
    q3: str | None = Field(None, description="最想解决的问题")
    q4: list[str] = Field(default_factory=list, description="想要的功能，多选")
    q5: str | None = Field(None, description="是否第一次用电动牙刷：是 / 否")


class RecommendReq(BaseModel):
    answers: QuizAnswers
    explain: bool = Field(True, description="是否生成推荐理由（有 Key 时用大模型，否则用模板）")


class RouteReq(BaseModel):
    model: str | None = Field(None, description="型号名；不传或“我不确定”走通用建议")


class SetupReq(BaseModel):
    model: str | None = None
    first_time: bool = False
    sensitive: bool = False
    goal: str | None = None


class ReminderReq(BaseModel):
    model: str | None = None
    start_date: str = Field(..., description="开始使用日期，YYYY-MM-DD")
    subscribe: bool = Field(False, description="模拟订阅；默认关闭")


class SyncReq(BaseModel):
    answers: QuizAnswers | None = None
    consent: bool
    already_synced: bool = False


class AskReq(BaseModel):
    question: str
    model: str | None = None
    followup_done: bool = Field(False, description="已经追问过一次型号时为 true，不再追问")
    use_device_data: bool = Field(False, description="V2：附加模拟设备数据（仅智能款，仅作演示）")


@app.get("/health")
def health():
    return {"ok": True, **service.meta()}


@app.get("/quiz")
def get_quiz():
    return service.get_quiz()


@app.post("/recommend")
def recommend(req: RecommendReq):
    return service.recommend(req.answers.model_dump(), explain=req.explain)


@app.get("/models")
def models():
    return service.model_options()


@app.post("/route")
def route(req: RouteReq):
    return service.route(req.model)


@app.post("/setup")
def setup(req: SetupReq):
    return service.setup(req.model, req.first_time, req.sensitive, req.goal)


@app.post("/reminder")
def reminder(req: ReminderReq):
    try:
        return service.reminder(req.model, req.start_date, req.subscribe)
    except ValueError:
        raise HTTPException(422, "start_date 格式应为 YYYY-MM-DD") from None


@app.post("/profile-sync")
def profile_sync(req: SyncReq):
    return service.profile_sync(req.answers.model_dump() if req.answers else None, req.consent, req.already_synced)


@app.post("/ask")
def ask(req: AskReq):
    return service.ask(req.question, req.model, req.followup_done, req.use_device_data)
