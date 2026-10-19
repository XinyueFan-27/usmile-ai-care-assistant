"""usmile AI 护齿助手 Demo 的 HTTP 接口（FastAPI）+ 前端页面（web/）。

个人作品集项目，非 usmile 官方，未上线。接口说明见 docs/API.md。
启动：.venv/bin/uvicorn src.api:app --port 8000
  - 前端：http://127.0.0.1:8000/        （web/index.html，模拟微信小程序）
  - 接口：http://127.0.0.1:8000/api/... （交互文档：http://127.0.0.1:8000/docs）
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.core import service
from src.core.quota import client_ip

app = FastAPI(title="usmile AI 护齿助手 Demo API（个人作品集，非官方，未上线）", version="0.2.0")
api = APIRouter(prefix="/api")


@app.middleware("http")
async def remember_client_ip(request: Request, call_next):
    """记下访问者 IP，给大模型限流用（src/core/quota.py）。不记录、不存储。"""
    fwd = request.headers.get("x-forwarded-for", "")
    token = client_ip.set(fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown"))
    try:
        return await call_next(request)
    finally:
        client_ip.reset(token)
WEB_DIR = Path(__file__).resolve().parents[1] / "web"


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
    use_device_data: bool = Field(False, description="V2：附加模拟设备数据（仅智能款、问题与刷牙习惯相关时，仅作演示）")
    profile: dict | None = Field(None, description="测评第 2–5 题（可含 q2_custom 等自己填写的内容），不含预算；只作用户情况参考")


@api.get("/health")
def health():
    return {"ok": True, **service.meta()}


@api.get("/quiz")
def get_quiz():
    return service.get_quiz()


@api.post("/recommend")
def recommend(req: RecommendReq):
    return service.recommend(req.answers.model_dump(), explain=req.explain)


@api.get("/models")
def models():
    return service.model_options()


@api.post("/route")
def route(req: RouteReq):
    return service.route(req.model)


@api.post("/setup")
def setup(req: SetupReq):
    return service.setup(req.model, req.first_time, req.sensitive, req.goal)


@api.post("/reminder")
def reminder(req: ReminderReq):
    try:
        return service.reminder(req.model, req.start_date, req.subscribe)
    except ValueError:
        raise HTTPException(422, "start_date 格式应为 YYYY-MM-DD") from None


@api.post("/profile-sync")
def profile_sync(req: SyncReq):
    return service.profile_sync(req.answers.model_dump() if req.answers else None, req.consent, req.already_synced)


@api.post("/ask")
def ask(req: AskReq):
    return service.ask(req.question, req.model, req.followup_done, req.use_device_data, req.profile)


@api.get("/sources")
def sources():
    """来源清单：编号 → 名称、链接（kb/sources.md）。"""
    return service.sources()


@api.get("/kb/{chunk_id}")
def kb_note(chunk_id: str):
    """单条知识库要点 + 出处（前端用于 App 下载、绑定说明等固定内容）。"""
    return service.kb_note(chunk_id)


app.include_router(api)
class NoCacheStatic(StaticFiles):
    """页面文件不缓存：前端改动后刷新就能看到（Demo 用）。"""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


if WEB_DIR.exists():
    app.mount("/", NoCacheStatic(directory=WEB_DIR, html=True), name="web")
