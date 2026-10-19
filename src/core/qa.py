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
from .config import DISCLAIMER, FALLBACK_LABEL, KB_SUMMARY_LABEL, MOCK_LABEL, PENDING, SIMULATED_LABEL
from .kb import Chunk, chunk_by_id, citation, default_chunks
from .llm_router import generate
from .retriever import THRESHOLD, default_index

FOLLOWUP_TEXT = "你用的是哪一款？"
NEEDS_MODEL = r"续航|电池|充一次|充满|充电多久|几档|档位|多少档|几个模式|有哪些模式|防水"
DEVICE_SETTING = r"模式|档位|设置|默认|app|绑定|连接|扫动|力度|语音|壁纸|ota|升级"
NO_EVIDENCE = "NO_EVIDENCE"
# 功效类和“默认是…”类说法：回答里出现但引用的资料原文里没有，就不采用（PRD 2.5 不输出功效承诺）
CLAIM_WORDS = ["能刷干净", "可以刷干净", "刷得干净", "清洁干净", "彻底清洁", "有效清洁", "有效去除", "美白", "治疗", "治愈",
               "预防", "根治", "消炎"]
DEFAULT_CLAIM = r"默认(模式|档位)?(是|为)"  # “默认是…”类结论也要原文写明“默认”（v1/v2 E-23）
HIGH_SCORE = {"bge": 0.55, "tfidf": 0.25}
BRUSH_HEAD_LIFE = r"刷头.{0,8}(多久|换|更换|炸毛|寿命|几个月)|炸毛"

SYSTEM = """你是 usmile 电动牙刷的使用助手，只依据“资料区”的内容回答用户问题。
规则：
1. 结论在前，200 字以内，简单中文。每个事实后面用 [编号] 标出资料编号，例如 [1]。
2. 资料区里没有依据的内容不要回答。资料能回答问题的全部或一部分时，就回答这一部分；只有资料和问题完全无关时，才只输出 NO_EVIDENCE。
3. 只说资料里明确写到的内容，资料没写的不要推断。问到资料没写的具体设置（例如默认是哪个模式、能不能切换或自定义），直接说“官方资料没有写这一点”，不要给出结论。
4. 答案因型号不同时，分型号说明；不要把一个型号的参数说成另一个型号的。
5. 每个 [编号] 只标在它真正支持的那句话后面。
6. 不诊断、不推荐药物；涉及不适时提示看牙医。不评价其他品牌，不承诺功效，不编造参数和型号。"""
DEVICE_RULE = """
7. 下面提供了“用户牙刷数据摘要”（模拟设备数据）：只用来给出个性化提醒，并在开头写“参考了你的牙刷数据”；不复述完整报告，不根据数据推断疾病。"""


def unsupported_claim(text: str, cited: list[Chunk]) -> str | None:
    source = " ".join(c.body for c in cited)
    if re.search(DEFAULT_CLAIM, text) and "默认" not in source:
        return "默认"
    return next((w for w in CLAIM_WORDS if w in text and w not in source), None)


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


def _generate(question: str, hits, model, device_summary, use_llm, profile=None) -> tuple[str, str]:
    """返回 (回答, mode)。mode 为 llm:<模型名> / fallback / mock。回答为 NO_EVIDENCE 表示资料不足。"""
    from src import llm  # 延迟导入
    if use_llm and llm.has_key():
        material = "\n\n".join(f"[{i}] {c.title}（适用：{c.applies_to}）\n{c.body}" for i, (c, _) in enumerate(hits, 1))
        user = f"资料区：\n{material}\n\n"
        if model:
            user += f"用户的型号：{model}\n"
        if profile:
            # 测评第 2–5 题（含自己填写），不含预算（D46 ⑥）；只用来判断哪些资料和用户相关，不是事实依据
            user += f"用户在选购测评里说的情况（用户自述，不是资料，不能当作出处）：{profile}\n"
        if device_summary:
            user += f"用户牙刷数据摘要（{SIMULATED_LABEL}）：{device_summary}\n"
        user += f"用户问题：{question}"
        try:
            system = SYSTEM + (DEVICE_RULE if device_summary else "")
            reply, used = generate([{"role": "system", "content": system}, {"role": "user", "content": user}])
            reply = reply.strip()
            # 模型有时在正常回答后面再附一个 NO_EVIDENCE：有正文就去掉标记，只有标记才算没有依据
            body = reply.replace(NO_EVIDENCE, "").strip().lstrip("。，.,：:；; ")
            if not re.sub(r"[\s。，.,！!？?]", "", body):  # 只剩标点也算没有依据
                body = ""
            return (body or NO_EVIDENCE), f"llm:{used}"
        except Exception:  # noqa: BLE001  模型服务不可用（如限流）时退回资料要点，界面如实标明
            lines = [FALLBACK_LABEL] + [f"[{i}] {c.summary}" for i, (c, _) in enumerate(hits[:2], 1)]
            return "\n".join(lines), "fallback"
    lines = [MOCK_LABEL]
    lines += [f"[{i}] {c.summary}" for i, (c, _) in enumerate(hits[:2], 1)]
    return "\n".join(lines), "mock"


def confirmed_models(catalog: Catalog) -> list[str]:
    """App 支持情况已确认的型号（追问选项用，D46 ⑫）；属性表缺失时用知识库里有详细资料的型号。"""
    names = [m.name for m in catalog.models if m.app_status in ("smart", "basic")]
    return names or kb_model_names()


def answer(question: str, catalog: Catalog, model: str | None = None, followup_done: bool = False,
           device_summary: dict | None = None, use_llm: bool = True, index=None, k: int = 4,
           profile: dict | None = None) -> dict:
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
        return _base("followup", FOLLOWUP_TEXT, followup_options=confirmed_models(catalog) + ["我不确定"])

    # 3. 检索
    index = index or default_index()
    query = f"{model} {question}" if model else question
    hits = _rerank(index.search(query, k=k), model)
    if not hits or hits[0][1] < THRESHOLD[index.kind]:
        return _no_evidence(index.label)

    # 4. 生成
    text, mode = _generate(question, hits, model, device_summary, use_llm, profile)
    mode, _, llm_model = mode.partition(":")
    # 出处编号：[1]、[2, 4]、[2，4] 都认
    nums = [n for grp in re.findall(r"\[([\d,，、\s]+)\]", text) for n in re.findall(r"\d+", grp)]
    used = sorted({int(n) for n in nums if 1 <= int(n) <= len(hits)})
    problem = None
    if text.startswith(NO_EVIDENCE):
        problem = "no_evidence"
    elif not used:  # 有结论必须有出处；模型没标出处就不采用
        problem = "no_citation"
    elif unsupported_claim(text, [hits[i - 1][0] for i in used]):  # 功效词不在引用原文里（v2 bad case）
        problem = "claim"
    if problem:
        if hits[0][1] >= HIGH_SCORE[index.kind]:
            # 资料明显相关，只是模型没整理好：直接给官方资料要点并标明（不该拒却拒了，v1/v2 bad case）
            res = _base("answer", "\n".join([KB_SUMMARY_LABEL] + [f"[{i}] {c.summary}" for i, (c, _) in enumerate(hits[:2], 1)]),
                        mode="kb_summary", llm_model=llm_model or None, retriever=index.label,
                        citations=[citation(c) for c, _ in hits[:2]], dropped=problem)
        else:
            res = {**_no_evidence(index.label), "llm_model": llm_model or None, "dropped": problem}
    else:
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
    if re.search(BRUSH_HEAD_LIFE, question):  # 刷头更换类：固定给官方周期和提醒入口（v1 bad case 3）
        head = chunk_by_id("KB-HEAD-01")
        if head:
            res["notices"].append(f"官方更换周期：{head.title.split('：')[-1]}（{head.chunk_id}）。")
            if all(c["chunk_id"] != head.chunk_id for c in res["citations"]):
                res["citations"].append(citation(head))
        res["notices"].append({"smart": "你的型号可以在笑容加 App 里查看刷头使用天数和更换提醒。",
                               "basic": "可以在首次设置页填写开始使用日期，开启刷头更换提醒。"}.get(
            route_path, "基础款可以在小程序开启刷头更换提醒；智能款在笑容加 App 里查看。"))
    if device_summary:
        res["simulated"] = True
        res["notices"].insert(0, f"参考了你的牙刷数据（{SIMULATED_LABEL}），数据更新时间：{device_summary.get('updated_at', '模拟')}")
        # 设备数据的个性化提醒用规则加，不依赖模型是否用上（v1 bad case 2）
        if "较多" in str(device_summary.get("force_overuse", "")):
            res["notices"].append(f"你的牙刷数据显示近期力度过大次数较多（{SIMULATED_LABEL}），刷牙时注意减轻按压力度。")
    res["model"] = model
    return res
