"""usmile AI 护齿助手 Demo（Streamlit，模拟微信小程序形态）。

个人作品集项目，非 usmile 官方，未上线。
启动：.venv/bin/streamlit run app.py
界面只负责展示和记录本地状态；所有判断都在 src/core/service.py（与 src/api.py 的 HTTP 接口同一层），
以后换成真实小程序只重写这一层界面。
"""

import json
from datetime import date

import streamlit as st

from src.core import service
from src.core.config import FALLBACK_LABEL, KB_SUMMARY_LABEL, MOCK_LABEL
from src.core.examples import EXAMPLES
from src.core.kb import default_sources

st.set_page_config(page_title="usmile AI 护齿助手（作品集 Demo）", page_icon="🦷", layout="centered")

st.markdown(
    """
<style>
:root{--brand:#007cfa;--brand-weak:#e6f2ff;--sub:#646a73;--line:#e5e6eb;--warn:#d83931;--warn-weak:#fdecea;
--amber:#b25e00;--amber-weak:#fff4e5;--ph-bg:#eceef1;--ph-text:#8f959e}
.block-container{max-width:420px;padding:1rem 16px 2rem}
header[data-testid="stHeader"]{display:none}
.nav{background:#fff;border-bottom:1px solid var(--line);text-align:center;font-weight:600;padding:10px 0;margin:-1rem -16px 12px}
.card{background:#fff;border-radius:12px;padding:14px;margin:8px 0;border:1px solid var(--line)}
.hero{background:linear-gradient(160deg,#aedbfc 0%,#e6f2ff 60%,#fff 100%);border-radius:14px;padding:18px;margin-bottom:8px}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;background:var(--brand-weak);color:#0062c4;margin:2px 4px 2px 0}
.assume{background:var(--amber-weak);color:var(--amber)}
.warn{background:var(--warn-weak);border-color:#f5c2be}
.sim{border:2px dashed var(--warn);color:var(--warn);border-radius:8px;padding:6px 10px;font-weight:600;margin:6px 0;font-size:13px}
.mock{background:var(--amber-weak);color:var(--amber);border-radius:8px;padding:6px 10px;font-size:13px;margin:6px 0}
.src{font-size:12px;color:var(--sub);margin-top:6px}
.src a{color:var(--brand)}
.disc{font-size:12px;color:var(--sub);margin-top:8px}
.foot{font-size:12px;color:var(--ph-text);text-align:center;margin-top:24px;border-top:1px solid var(--line);padding-top:8px}
.pending{color:var(--ph-text)}
</style>
""",
    unsafe_allow_html=True,
)

META = service.meta()
SOURCES = default_sources()
ss = st.session_state
ss.setdefault("page", "home")
ss.setdefault("answers", {})
ss.setdefault("step", 0)
ss.setdefault("model", None)
ss.setdefault("chat", [])
ss.setdefault("synced", False)
ss.setdefault("identity", "未购")


def go(page: str):
    ss.page = page
    st.rerun()


def nav(title: str, back: str | None = None):
    st.markdown(f'<div class="nav">{title}</div>', unsafe_allow_html=True)
    if back and st.button("‹ 返回", key=f"back_{title}"):
        go(back)


def esc(text: str) -> str:
    return str(text).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def show_value(text: str) -> str:
    t = esc(text)
    return t.replace("【待知识库】", '<span class="pending">【待知识库】</span>')


def src_html(ids: list[str]) -> str:
    if not ids:
        return ""
    parts = []
    for i in ids:
        s = SOURCES.get(i)
        parts.append(f'<a href="{s["url"]}" target="_blank">{i} {esc(s["name"])}</a>' if s and s["url"] else esc(i))
    return '<div class="src">出处：' + "；".join(parts) + "（抓取日期 2026-10-18）</div>"


def cite_html(citations: list[dict]) -> str:
    if not citations:
        return ""
    rows = []
    for c in citations:
        links = "、".join(
            f'<a href="{s["url"]}" target="_blank">{esc(s["name"])}</a>' if s.get("url") else esc(s["name"]) for s in c["sources"]
        )
        rows.append(f'{c["chunk_id"]} {esc(c["title"])}｜{links}｜{c["fetched"]}')
    return '<div class="src">出处：<br>' + "<br>".join(rows) + "</div>"


def model_note(model: str | None) -> str:
    """注明这条内容由哪个模型生成；用了备用模型时写明（D41）。"""
    if not model:
        return ""
    tag = "（主模型限流，已换用备用模型）" if model != META["llm_primary"] else ""
    return f'<div class="src">由 {esc(model)} 生成{tag}</div>'


def footer():
    st.markdown(
        f'<div class="disc">{META["disclaimer"]}</div><div class="foot">{META["footer"]}<br>'
        f'模型：{META["llm_primary"] + "（备用 " + META["llm_fallback"] + "）" if META["llm_mode"] == "llm" else "mock 模式"}｜检索：{META["retriever"]}</div>',
        unsafe_allow_html=True,
    )


# ---------------- 首页 ----------------
def page_home():
    nav("usmile AI 护齿助手")
    st.markdown(
        '<div class="hero"><b style="font-size:18px">选牙刷、学用法，问我就行</b><br>'
        '<span style="font-size:13px;color:#646a73">不用登录。个人作品集 Demo，非 usmile 官方。</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("还没买，帮我选", type="primary", use_container_width=True):
        ss.answers, ss.step = {}, 0
        go("quiz")
    if st.button("已经买了，教我用", use_container_width=True):
        go("route")
    if st.button("直接提问 ›", use_container_width=True):
        go("chat")
    footer()


# ---------------- 选购测评 ----------------
def page_quiz():
    qs = service.get_quiz()["questions"]
    assume = set(service.get_quiz()["business_assumption"])
    i = ss.step
    q = qs[i]
    nav("选购测评", back="home" if i == 0 else None)
    st.progress((i + 1) / len(qs), text=f"{i + 1}/{len(qs)}")
    st.markdown(f"**{q['text']}**" + ("（必答）" if q.get("required") else ""))
    if q.get("note"):
        st.caption(q["note"])
    fmt = lambda o: f"{o}（业务假设）" if o in assume else o  # noqa: E731
    cur = ss.answers.get(q["id"])
    if q["type"] == "single":
        idx = q["options"].index(cur) if cur in q["options"] else None
        val = st.radio(q["text"], q["options"], index=idx, format_func=fmt, label_visibility="collapsed", key=f"r_{q['id']}")
    else:
        st.caption("可多选，也可以不选")
        val = [o for o in q["options"] if st.checkbox(fmt(o), value=o in (cur or []), key=f"c_{q['id']}_{o}")]
        if q.get("exclusive") in val and len(val) > 1:
            st.warning(f"“{q['exclusive']}”不能和其他选项同时选")
    ss.answers[q["id"]] = val
    c1, c2 = st.columns(2)
    if i > 0 and c1.button("上一题", use_container_width=True):
        ss.step -= 1
        st.rerun()
    last = i == len(qs) - 1
    if c2.button("看推荐" if last else "下一题", type="primary", use_container_width=True):
        if q.get("required") and not val:
            st.error("请先选择预算")
        elif q["type"] == "multi" and q.get("exclusive") in val and len(val) > 1:
            st.error("请修改互斥的选项")
        elif last:
            go("rec")
        else:
            ss.step += 1
            st.rerun()
    footer()


# ---------------- 推荐卡 ----------------
def model_card(card: dict, title: str):
    reasons = card.get("reasons", {})
    html = f'<div class="card"><span class="tag">{title}</span><br><b style="font-size:17px">{esc(card["model"])}</b>'
    html += f'　<span style="color:#646a73">京东官方自营店标价 ¥{show_value(card["price"])}</span>'
    html += src_html(card["price_sources"])
    html += f'<div style="margin-top:8px"><b>推荐刷头</b>：{show_value(card["brush_head"]["text"])}</div>{src_html(card["brush_head"]["sources"])}'
    html += '<div style="margin-top:8px"><b>推荐理由</b>' + ("（模板文案）" if reasons.get("by") == "template" else "（大模型根据官方参数撰写）") + "</div>"
    for r in reasons.get("reasons", []):
        html += f'<div>· {esc(r["reason"])}</div>{src_html(r.get("sources", []))}'
    html += model_note(reasons.get("llm_model"))
    st.markdown(html + "</div>", unsafe_allow_html=True)


def page_rec():
    nav("为你推荐", back="quiz")
    # 推荐结果（含大模型写的理由）只在答案变化时算一次；点页面上其他按钮不再重新调用大模型
    key = json.dumps(ss.answers, ensure_ascii=False, sort_keys=True)
    if ss.get("rec_key") != key:
        with st.spinner("正在生成推荐理由…"):
            ss.rec = service.recommend(ss.answers)
        ss.rec_key = key
    res = ss.rec
    if res["status"] == "ok":
        model_card(res["main"], "主推")
        if res.get("backup"):
            model_card(res["backup"], "备选")
        st.caption(res["price_note"])
    elif res["status"] == "empty":
        st.markdown(f'<div class="card">{res["message"]}</div>', unsafe_allow_html=True)
        if st.button("调整预算", type="primary", use_container_width=True):
            ss.step = 0
            go("quiz")
    else:
        st.markdown(f'<div class="card">{show_value(res.get("message", "；".join(res.get("errors", []))))}</div>', unsafe_allow_html=True)
    if res.get("notes"):
        html = '<div class="card warn"><b>使用注意</b>'
        for n in res["notes"]:
            html += f'<div>· {esc(n["text"])}</div>{src_html(n["sources"])}'
        st.markdown(html + "</div>", unsafe_allow_html=True)
    if res["status"] == "ok":
        c1, c2 = st.columns(2)
        if c1.button("去购买", use_container_width=True):
            st.info("Demo 不跳转商城（跳转商城还是电商【待核实】）。")
        if c2.button("符合我的情况 👍", use_container_width=True):
            st.toast("已记录（仅本次会话，不上传）")
        if st.button("买好了 → 按型号继续", type="primary", use_container_width=True):
            ss.model = res["main"]["model"]
            go("route")
    if st.button("有问题？去提问", use_container_width=True):
        go("chat")
    footer()


# ---------------- 按型号分流 ----------------
def page_route():
    nav("选择你的型号", back="home")
    opts = service.model_options()
    if not opts["available"]:
        st.markdown('<div class="card pending">型号列表【待知识库】</div>', unsafe_allow_html=True)
    choices = [f"智能款｜{m}" for m in opts["smart"]] + [f"基础款｜{m}" for m in opts["basic"]] + [opts["unsure"]]
    default = next((k for k, c in enumerate(choices) if ss.model and c.endswith(f"｜{ss.model}")), len(choices) - 1)
    pick = st.radio("型号", choices, index=default, label_visibility="collapsed")
    st.caption("智能款 = 支持笑容加 App（以 usmile 官网下载中心和型号页为准）；基础款 = 官方确认没有 App 功能。"
               f"App 支持情况待核实的型号（{'、'.join(opts['unverified']) or '无'}）暂不列出，可选“我不确定”。")
    if st.button("确认型号", type="primary", use_container_width=True):
        ss.model = None if pick == opts["unsure"] else pick.split("｜", 1)[1]
        r = service.route(ss.model)
        ss.identity = {"smart": "智能款", "basic": "基础款", "unsure": "基础款"}[r["path"]]
        go("bind" if r["path"] == "smart" else "setup")
    footer()


# ---------------- 智能款：引导绑定 App ----------------
def page_bind():
    nav("用笑容加 App 管理牙刷", back="route")
    st.markdown(
        f'<div class="card"><b>{esc(ss.model)}</b> 支持笑容加 App。设备设置、刷牙报告、刷头记录与提醒都在 App 里，小程序不重复做。</div>',
        unsafe_allow_html=True,
    )
    st.link_button("下载笑容加 App（usmile 官网下载中心）", "https://www.usmile.com/cn/download", use_container_width=True)
    st.markdown(src_html(["S10"]), unsafe_allow_html=True)
    if st.button("去 App 绑定", type="primary", use_container_width=True):
        go("sync" if ss.answers.get("q1") else "bound")
    if st.button("已绑定，去 App 设置", use_container_width=True):
        st.info("Demo 不跳转 App（跳转方式【待知识库】）。绑定步骤以 App 内指引为准。")
    if st.button("有问题？去提问", use_container_width=True):
        go("chat")
    footer()


def page_sync():
    nav("同步测评结果", back="bind")
    st.markdown(
        '<div class="card">绑定时可以把你在小程序做的测评结果同步给 App 一次，用于 App 一开始的建议。<br><b>只同步这 4 项：</b>'
        "<br>· 牙齿情况<br>· 最想解决的问题<br>· 想要的功能<br>· 是否第一次用电动牙刷<br><b>不同步预算。</b>"
        '<br><span class="pending">撤回方式【待知识库】</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    if c1.button("同意并去绑定", type="primary", use_container_width=True):
        ss.sync_result = service.profile_sync(ss.answers, True, ss.synced)
        ss.synced = True
        go("bound")
    if c2.button("不同步，去绑定", use_container_width=True):
        ss.sync_result = service.profile_sync(ss.answers, False)
        go("bound")
    footer()


def page_bound():
    nav("去 App 绑定", back="bind")
    r = ss.get("sync_result")
    if r:
        st.markdown(f'<div class="card">{esc(r["message"])}</div>', unsafe_allow_html=True)
        if r.get("synced"):
            st.json(r["synced"])
    st.info("Demo 不连接真实 App。绑定步骤以笑容加 App 内指引为准。")
    if st.button("回首页", use_container_width=True):
        go("home")
    footer()


# ---------------- 基础款：首次设置 + 刷头提醒 ----------------
def page_setup():
    nav("首次设置", back="route")
    st.markdown(f"型号：**{esc(ss.model or '我不确定')}**")
    first = st.radio("是第一次用电动牙刷吗？", ["是", "否"], horizontal=True) == "是"
    sensitive = st.radio("牙龈敏感吗？", ["是", "否"], index=1, horizontal=True) == "是"
    goal = st.selectbox("最想改善什么？", ["刷不干净", "刷牙习惯不好", "牙黄", "护理牙龈"])
    if st.button("生成我的设置", type="primary", use_container_width=True):
        ss.setup_result = service.setup(ss.model, first, sensitive, goal)
    r = ss.get("setup_result")
    if r:
        if r["status"] == "general":
            st.markdown(f'<div class="card"><span class="tag">通用建议</span> 确认型号前只给通用建议。<br>'
                        f'查看型号的方法：{show_value(r["how_to_find_model"])}</div>', unsafe_allow_html=True)
        html = '<div class="card">'
        for it in r.get("items", []):
            html += f'<div style="margin-top:6px"><b>{esc(it["name"])}</b>：{show_value(it["text"])}</div>'
            html += src_html(it.get("sources", [])) + cite_html(it.get("citations", []))
        for n in r.get("notes", []):
            html += f'<div class="disc">· {esc(n)}</div>'
        st.markdown(html + "</div>", unsafe_allow_html=True)

    st.markdown("**刷头更换提醒**（模拟）")
    start = st.date_input("开始使用日期", value=date.today(), max_value=date.today())
    rem = service.reminder(ss.model, start.isoformat(), ss.get("subscribed", False))
    if rem["status"] == "ok":
        st.markdown(f'<div class="card">官方更换周期：{rem["cycle"]}{src_html(rem["cycle_sources"])}'
                    f'<b>下次更换日期：{rem["next_date"]}</b><div class="disc">{rem["message"]}</div></div>', unsafe_allow_html=True)
        if not ss.get("subscribed") and st.button("提醒我", use_container_width=True):
            ss.ask_subscribe = True
        if ss.get("ask_subscribe") and not ss.get("subscribed"):
            st.warning("（模拟）是否允许发送 1 条刷头更换提醒？真实订阅消息规则【待知识库】")
            c1, c2 = st.columns(2)
            if c1.button("允许", use_container_width=True):
                ss.subscribed, ss.ask_subscribe = True, False
                st.rerun()
            if c2.button("拒绝", use_container_width=True):
                ss.ask_subscribe = False
                st.rerun()
        if ss.get("subscribed") and st.button("取消提醒", use_container_width=True):
            ss.subscribed = False
            st.rerun()
    else:
        st.markdown(f'<div class="card">{show_value(rem.get("message") or "更换周期【待知识库】")}</div>', unsafe_allow_html=True)
    if st.button("有问题？去提问", use_container_width=True):
        go("chat")
    footer()


# ---------------- 护齿问答 ----------------
def run_ask(question: str, followup_done: bool = False, model: str | None = None):
    m = model or (ss.model if ss.identity != "未购" else None)
    with st.spinner("正在查找官方资料…"):
        res = service.ask(question, m, followup_done, use_device_data=ss.get("use_device", False))
    ss.chat.append({"q": question, "res": res})
    if res["type"] == "boundary":
        ss.boundary = res
        go("boundary")


def render_answer(item: dict, k: int):
    res = item["res"]
    st.markdown(f'<div class="card" style="background:#e6f2ff;margin-left:40px">{esc(item["q"])}</div>', unsafe_allow_html=True)
    html = '<div class="card">'
    if res.get("simulated"):
        html += f'<div class="sim">{META["simulated_label"]}</div>'
    text = res["answer"]
    for mode, label in (("mock", MOCK_LABEL), ("fallback", FALLBACK_LABEL), ("kb_summary", KB_SUMMARY_LABEL)):
        if res.get("mode") == mode:
            html += f'<div class="mock">{label}</div>'
            text = text.replace(label, "").strip()
    if res["type"] == "subjective":
        html += '<span class="tag">体验因人而异</span><br>'
    html += esc(text)
    for n in res.get("notices", []):
        html += f'<div style="margin-top:6px;color:#b25e00">· {esc(n)}</div>'
    html += cite_html(res.get("citations", []))
    html += model_note(res.get("llm_model"))
    html += f'<div class="disc">{res["disclaimer"]}</div></div>'
    st.markdown(html, unsafe_allow_html=True)
    if "go_app" in res.get("actions", []):
        st.link_button("去笑容加 App 设置", "https://www.usmile.com/cn/download", use_container_width=True)
    if "start_quiz" in res.get("actions", []) and st.button("做 5 题选购测评", key=f"quiz_{k}"):
        ss.answers, ss.step = {}, 0
        go("quiz")
    if res["type"] == "followup" and k == len(ss.chat) - 1:
        cols = st.columns(3)
        for j, opt in enumerate(res["followup_options"]):
            if cols[j % 3].button(opt, key=f"fu_{k}_{j}"):
                run_ask(item["q"], followup_done=True, model=None if opt == "我不确定" else opt)
                st.rerun()
    if res["type"] in ("answer", "no_evidence", "subjective"):
        c1, c2 = st.columns(2)
        if c1.button("已解决", key=f"ok_{k}"):
            st.toast("已记录（仅本次会话，不上传）")
        if c2.button("没解决", key=f"no_{k}"):
            st.toast("已记录。可以联系官方客服或换个说法再问。")


def page_chat():
    nav("护齿问答", back="home")
    opts = service.model_options()
    ids = ["未购", "智能款", "基础款"]
    ss.identity = st.radio("演示身份", ids, index=ids.index(ss.identity), horizontal=True)
    if ss.identity == "智能款":
        if ss.model not in opts["smart"]:
            ss.model = opts["smart"][0] if opts["smart"] else None
        ss.model = st.selectbox("型号", opts["smart"] or ["【待知识库】"], index=(opts["smart"] or [None]).index(ss.model) if ss.model in opts["smart"] else 0)
        ss.use_device = st.toggle("V2：结合我的牙刷数据（模拟设备数据，仅作演示，非真实用户）", value=ss.get("use_device", False))
    elif ss.identity == "基础款":
        choices = opts["basic"] + ["我不确定"]
        cur = ss.model if ss.model in choices else choices[0]
        pick = st.selectbox("型号", choices, index=choices.index(cur))
        ss.model = None if pick == "我不确定" else pick
        ss.use_device = False
    else:
        ss.use_device = False
    if ss.get("use_device"):
        st.markdown(f'<div class="sim">{META["simulated_label"]}：已授权的设备数据摘要只用于个性化问答，不展示完整报告</div>', unsafe_allow_html=True)
    with st.expander("示例问题（京东买家提问 / 评论原文）"):
        for i, (qid, text) in enumerate(EXAMPLES):
            if st.button(text, key=f"ex_{i}"):
                run_ask(text)
                st.rerun()
    for k, item in enumerate(ss.chat):
        render_answer(item, k)
    q = st.chat_input("输入你的问题")
    if q:
        run_ask(q)
        st.rerun()
    if ss.chat and st.button("清空对话"):
        ss.chat = []
        st.rerun()
    footer()


# ---------------- 安全边界 ----------------
def page_boundary():
    res = ss.get("boundary") or {}
    nav(res.get("title", "提示"), back="chat")
    urgent = res.get("category") == "urgent"
    st.markdown(
        f'<div class="card warn"><b style="font-size:{22 if urgent else 17}px">{esc(res.get("title", ""))}</b>'
        f'<div style="margin-top:8px">{esc(res.get("answer", ""))}</div>{cite_html(res.get("citations", []))}'
        f'<div class="disc">{res.get("disclaimer", "")}</div></div>',
        unsafe_allow_html=True,
    )
    if "start_quiz" in res.get("actions", []) and st.button("按我的需求推荐（做测评）", type="primary", use_container_width=True):
        ss.answers, ss.step = {}, 0
        go("quiz")
    if st.button("返回问答", use_container_width=True):
        go("chat")
    footer()


PAGES = {"home": page_home, "quiz": page_quiz, "rec": page_rec, "route": page_route, "bind": page_bind,
         "sync": page_sync, "bound": page_bound, "setup": page_setup, "chat": page_chat, "boundary": page_boundary}
PAGES[ss.page]()
