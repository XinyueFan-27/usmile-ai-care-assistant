"""护齿问答（PRD 2.3.5、6.1 LLM 2）。

处理顺序：
1. 安全边界规则（safety.classify），命中就不调用大模型。
2. 答案依赖型号但不知道型号 → 先追问一次“你用的是哪一款？”。
3. 检索 kb/；最高相似度低于阈值 → 如实说“没有找到可靠的官方资料”，给官方客服入口。
4. 有 Key：GLM 只依据检索到的资料回答，正文用 [n] 标出处；回答里没有有效出处就当作没有依据。
   没有 Key：mock 模式，直接列出检索到的资料要点，并标明是 mock。
5. 附加规则：智能款问设备设置 → “去 App 设置”入口；正畸 → 提示咨询正畸医生；出血 → 提示持续出血看牙医；
   每条回答都带免责声明。
"""

from __future__ import annotations

import re

from . import safety
from .catalog import Catalog
from .config import DISCLAIMER, FALLBACK_LABEL, MOCK_LABEL, PENDING, SIMULATED_LABEL
from .kb import Chunk, chunk_by_id, citation, default_chunks
from .llm_router import generate
from .retriever import THRESHOLD, default_index

FOLLOWUP_TEXT = "你用的是哪一款？"
NEEDS_MODEL = r"续航|电池|充一次|充满|充电多久|几档|档位|多少档|几个模式|有哪些模式|防水"
DEVICE_SETTING = r"模式|档位|设置|默认|app|绑定|连接|扫动|力度|语音|壁纸|ota|升级"
NO_EVIDENCE = "NO_EVIDENCE"

SYSTEM = """你是 usmile 电动牙刷的使用助手，只依据“资料区”的内容回答用户问题。
规则：
1. 结论在前，200 字以内，简单中文。每个事实后面用 [编号] 标出资料编号，例如 [1]。
2. 资料区里没有依据的内容不要回答。资料能回答问题的全部或一部分时，就回答这一部分；只有资料和问题完全无关时，才只输出 NO_EVIDENCE。
3. 只说资料里明确写到的内容，资料没写的不要推断（例如资料没说能不能切换，就不要说能或不能）。
4. 不诊断、不推荐药物；涉及不适时提示看牙医。不评价其他品牌，不承诺功效，不编造参数和型号。"""
DEVICE_RULE = """
5. 下面提供了“用户牙刷数据摘要”（模拟设备数据）：只用来给出个性化提醒，并在开头写“参考了你的牙刷数据”；不复述完整报告，不根据数据推断疾病。"""


def kb_model_names(chunks=None) -> list[str]:
    """知识库 models/ 下有详细资料的型号（属性表缺失时作为追问选项）。"""
    names = []
    for c in chunks if chunks is not None else default_chunks():
        if c.path.startswith("models/") and c.path not in ("models/lineup.md", "models/others.md"):
            a = c.applies_to
            if a and a not in names and "通用" not in a:
                names.append(a)
    return names


def detect_model(question: str, names: list[str]) -> str | None:
    q = question.replace(" ", "").lower()
    for n in sorted(names, key=len, reverse=True):
        if n.replace(" ", "").lower() in q:
            return n
    return None


def _rerank(hits: list[tuple[Chunk, float]], model: str | None) -> list[tuple[Chunk, float]]:
    if not model:
        return hits
    key = model.replace(" ", "").lower()
    out = []
    for c, s in hits:
        applies = c.applies_to.replace(" ", "").lower()
        if key in applies:
            s += 0.1
        elif re.search(r"[a-z]\d{1,2}", applies) and "通用" not in applies and "全系列" not in applies:
            s -= 0.1  # 明确写着别的型号
        out.append((c, s))
    return sorted(out, key=lambda x: -x[1])


def _base(kind: str, answer: str, **kw) -> dict:
    return {"type": kind, "answer": answer, "citations": [], "actions": [], "notices": [],
            "mode": "rule", "llm_model": None, "retriever": None, "followup_options": [], "disclaimer": DISCLAIMER,
            "simulated": False, **kw}


def _no_evidence(retriever_label: str) -> dict:
    svc = chunk_by_id("KB-SVC-01")
    text = "没有找到可靠的官方资料，暂时无法回答这个问题。可以联系官方客服确认"
    text += f"：{svc.summary}" if svc else f"：{PENDING}"
    return _base("no_evidence", text, citations=[citation(svc)] if svc else [],
                 actions=["contact_service"], retriever=retriever_label)


def _generate(question: str, hits, model, device_summary, use_llm) -> tuple[str, str]:
    """返回 (回答, mode)。mode 为 llm:<模型名> / fallback / mock。回答为 NO_EVIDENCE 表示资料不足。"""
    from src import llm  # 延迟导入
    if use_llm and llm.has_key():
        material = "\n\n".join(f"[{i}] {c.title}（适用：{c.applies_to}）\n{c.body}" for i, (c, _) in enumerate(hits, 1))
        user = f"资料区：\n{material}\n\n"
        if model:
            user += f"用户的型号：{model}\n"
        if device_summary:
            user += f"用户牙刷数据摘要（{SIMULATED_LABEL}）：{device_summary}\n"
        user += f"用户问题：{question}"
        try:
            system = SYSTEM + (DEVICE_RULE if device_summary else "")
            reply, used = generate([{"role": "system", "content": system}, {"role": "user", "content": user}])
            reply = reply.strip()
            # 模型有时在正常回答后面再附一个 NO_EVIDENCE：有正文就去掉标记，只有标记才算没有依据
            body = reply.replace(NO_EVIDENCE, "").strip()
            if not re.sub(r"[\s。，.,！!？?]", "", body):  # 只剩标点也算没有依据
                body = ""
            return (body or NO_EVIDENCE), f"llm:{used}"
        except Exception:  # noqa: BLE001  模型服务不可用（如限流）时退回资料要点，界面如实标明
            lines = [FALLBACK_LABEL] + [f"[{i}] {c.summary}" for i, (c, _) in enumerate(hits[:2], 1)]
            return "\n".join(lines), "fallback"
    lines = [MOCK_LABEL]
    lines += [f"[{i}] {c.summary}" for i, (c, _) in enumerate(hits[:2], 1)]
    return "\n".join(lines), "mock"


def answer(question: str, catalog: Catalog, model: str | None = None, followup_done: bool = False,
           device_summary: dict | None = None, use_llm: bool = True, index=None, k: int = 4) -> dict:
    question = (question or "").strip()
    if not question:
        return _base("invalid", "请输入问题。")

    # 1. 安全边界 / 主观口碑：先于大模型
    cat = safety.classify(question)
    if cat:
        r = safety.respond(cat)
        kind = "boundary" if cat in safety.BOUNDARY else "subjective"
        return _base(kind, r["answer"], category=cat, title=r["title"], citations=r["citations"], actions=r["actions"])

    names = catalog.names() or kb_model_names()
    model = model if model and model != "我不确定" else detect_model(question, names)

    # 2. 需要型号却不知道 → 追问一次
    if not model and not followup_done and re.search(NEEDS_MODEL, question, re.I):
        return _base("followup", FOLLOWUP_TEXT, followup_options=names + ["我不确定"])

    # 3. 检索
    index = index or default_index()
    query = f"{model} {question}" if model else question
    hits = _rerank(index.search(query, k=k), model)
    if not hits or hits[0][1] < THRESHOLD[index.kind]:
        return _no_evidence(index.label)

    # 4. 生成
    text, mode = _generate(question, hits, model, device_summary, use_llm)
    if text.startswith(NO_EVIDENCE):
        return {**_no_evidence(index.label), "llm_model": mode.partition(":")[2] or None}
    # 出处编号：[1]、[2, 4]、[2，4] 都认
    nums = [n for grp in re.findall(r"\[([\d,，、\s]+)\]", text) for n in re.findall(r"\d+", grp)]
    used = sorted({int(n) for n in nums if 1 <= int(n) <= len(hits)})
    if not used:  # 有结论必须有出处；模型没标出处就不采用
        return _no_evidence(index.label)
    mode, _, llm_model = mode.partition(":")
    res = _base("answer", text, mode=mode, llm_model=llm_model or None, retriever=index.label,
                citations=[citation(hits[i - 1][0]) for i in used])

    # 5. 附加规则
    route_path = catalog.find(model).app_status if model and catalog.find(model) else None
    if route_path == "smart" and re.search(DEVICE_SETTING, question, re.I):
        res["actions"].append("go_app")
        res["notices"].append("设备设置请在笑容加 App 里操作，小程序不提供设置。")
    if re.search(r"正畸|牙套|矫正", question):
        res["notices"].append("具体情况请咨询你的正畸医生。")
    if re.search(r"儿童|孩子|小孩|宝宝|小朋友", question):  # D39 ③：儿童不进测评，问答里引导看儿童系列
        kid = chunk_by_id("KB-LINE-02")
        res["notices"].append("usmile 有专门的儿童电动牙刷系列，可以查看儿童款。")
        if kid and all(c["chunk_id"] != kid.chunk_id for c in res["citations"]):
            res["citations"].append(citation(kid))
    if "出血" in question:
        res["notices"].append("持续出血请先看牙医。")
    if device_summary:
        res["simulated"] = True
        res["notices"].insert(0, f"参考了你的牙刷数据（{SIMULATED_LABEL}），数据更新时间：{device_summary.get('updated_at', '模拟')}")
        if mode in ("mock", "fallback") and device_summary.get("force_overuse") == "较多（模拟）":
            res["notices"].append("你的牙刷数据显示近期力度过大次数较多，刷牙时注意减轻按压力度。")
    res["model"] = model
    return res
