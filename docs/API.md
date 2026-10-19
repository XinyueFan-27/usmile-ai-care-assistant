# Demo 后端接口说明（v0.1）

> 个人作品集项目，非 usmile 官方，未上线。
> 这套接口是 Demo 的后端：Streamlit 前端（`app.py`）现在直接调用同一层函数（`src/core/service.py`）；以后换成微信小程序，只需要用小程序调用下面的 HTTP 接口，后端不用改。

## 启动

```bash
.venv/bin/uvicorn src.api:app --port 8000
```

启动后打开 http://127.0.0.1:8000/docs 可以在浏览器里直接试每个接口（FastAPI 自动生成）。

## 通用约定

- 请求和返回都是 JSON，UTF-8。
- 所有官方信息（型号、价格、参数、出处）只来自 `kb/`；没有依据的字段返回 `"【待知识库】"`，前端原样显示，不得补全。
- `sources` 是来源编号列表（如 `"S02"`），名称和链接见 `kb/sources.md`；问答的 `citations` 已带名称和链接。
- 每个页面都要显示 `GET /health` 返回的 `footer`（非官方说明）和 `disclaimer`（免责声明）。
- 主模型（`ZHIPU_MODEL`）被限流时自动换备用模型（`ZHIPU_FALLBACK_MODEL`），返回里的 `llm_model` 写明实际用的模型；`GET /health` 返回 `llm_primary` 和 `llm_fallback`。
- 没有配置大模型 Key 时 `llm_mode = "mock"`：问答返回检索到的资料要点，并在回答开头带 mock 标注；推荐理由用模板文案（`by = "template"`）。

## 接口一览

| 方法 | 路径 | 用途 | 对应 PRD |
|---|---|---|---|
| GET | `/health` | 运行状态、页脚、免责声明、是否 mock、检索方式 | — |
| GET | `/quiz` | 5 道测评题和选项 | 2.3.2 |
| POST | `/recommend` | 规则推荐 + 推荐理由 | 2.3.2、2.3.3 |
| GET | `/models` | 购后选型号页的选项（智能款 / 基础款 / 待核实） | 2.3.8 |
| POST | `/route` | 按型号分流 | 2.3.8 |
| POST | `/setup` | 首次设置建议（基础款 / 不确定型号） | 2.3.4 |
| POST | `/reminder` | 刷头更换日期 + 模拟订阅（基础款） | 2.3.7 |
| POST | `/profile-sync` | 画像同步（模拟，小程序 → App） | 2.3.10 |
| POST | `/ask` | 护齿问答（安全边界、追问、RAG、V2 模拟设备数据） | 2.3.5、2.3.6、2.3.9、2.3.11 |

## 详细说明

### POST /recommend

请求：

```json
{"answers": {"q1": "200 元以下", "q2": ["牙龈敏感或容易出血"], "q3": "护理牙龈", "q4": ["续航长"], "q5": "是"}, "explain": true}
```

返回 `status`：

| status | 含义 | 前端怎么显示 |
|---|---|---|
| `ok` | 有推荐 | `main`（主推）、`backup`（备选，可能为 null）、`notes`（注意事项）、`price_note` |
| `empty` | 预算内没有型号 | 显示 `message`，给“调整预算”入口，不展示任何型号 |
| `invalid` | 答案不合法（没选预算、互斥选项同时选） | 显示 `errors` |
| `pending_kb` | 型号属性表缺失 | 显示 `message`（含【待知识库】） |

`main` / `backup` 字段：`model`、`price`（京东官方自营店标价）、`price_sources`、`app_support`、`battery_days`、`brush_head`（`text` + `sources`）、`score`（命中选项数）、`matched`（每个命中选项的字段、原值、出处）、`reasons`（`reasons` 列表 + `by`：`llm` 或 `template` + `llm_model`）。

规则：预算硬筛 → 按命中选项数打分 → 同分取价格低 → 再按型号名。大模型只写理由，不选型号；理由里的数字不在官方参数中就整组换成模板。

### GET /models、POST /route

`/models` 返回 `smart`（支持笑容加 App）、`basic`（官方确认不支持）、`unverified`（是否支持【待核实】，不放进两个名单）、`unsure`（“我不确定”）。

`/route` 请求 `{"model": "P10"}`，返回 `path`（`smart` / `basic` / `unsure`）和 `features`：

| path | features | 说明 |
|---|---|---|
| `smart` | `go_app`、`qa` | 显示“去 App 设置”和问答，不显示首次设置和刷头提醒 |
| `basic` | `setup`、`reminder`、`qa` | 显示首次设置、刷头提醒和问答 |
| `unsure` | `setup_general`、`qa` | 型号不确定或 App 支持待核实：只给“通用建议” |

### POST /setup

请求 `{"model": "P10", "first_time": true, "sensitive": false}`。返回 `status`：`ok`（`items` 每项有 `name`、`text`、`sources`）/ `general`（标注“通用建议”）/ `not_applicable`（智能款，请去 App）。

### POST /reminder

请求 `{"model": "P10", "start_date": "2026-10-18", "subscribe": false}`。返回 `cycle`（官方更换周期）、`next_date`、`subscribed`。智能款返回 `not_applicable`；周期缺失返回 `pending_kb`。订阅是模拟的，不发送真实消息。

### POST /profile-sync

请求 `{"answers": {...}, "consent": true}`。只同步测评第 2–5 题（牙齿情况、最想解决的问题、想要的功能、是否新手），**不同步预算**；`consent=false` 返回 `declined` 且不同步；`already_synced=true` 返回 `already_synced`（只同步一次）。

### POST /ask

请求：

```json
{"question": "续航多久呀", "model": null, "followup_done": false, "use_device_data": false}
```

返回 `type`：

| type | 含义 |
|---|---|
| `boundary` | 命中安全边界（`category`：`urgent` 急症 / `medical` 医疗 / `service` 售后 / `authenticity` 真伪 / `competitor` 竞品），不调用大模型 |
| `subjective` | 主观口碑问题，不下结论 |
| `followup` | 需要型号：显示 `answer`（“你用的是哪一款？”）和 `followup_options`；用户选完后带 `model` 和 `followup_done=true` 再调一次 |
| `answer` | 正常回答：`citations`（知识块编号、标题、来源名称和链接、抓取日期）、`mode`（`llm` / `fallback` 大模型繁忙时的资料要点 / `mock`）、`llm_model`（实际用的模型，主模型限流时为备用模型）、`retriever`、`actions`（如 `go_app`）、`notices` |
| `no_evidence` | 没有找到可靠官方资料，附官方客服入口 |

所有返回都带 `disclaimer`。`use_device_data=true` 且型号是智能款时，附加 V2 模拟设备数据，返回 `simulated=true`，`notices` 第一条注明“参考了你的牙刷数据（模拟设备数据，仅作演示，非真实用户）”和更新时间。

## 换成小程序时要注意

- 小程序端只需要实现界面和本地状态（测评答案、型号、是否已追问），所有判断都在后端。
- 订阅消息、App 跳转、商城跳转在 Demo 里都是模拟的，真实接入规则【待核实】（PRD 14.1）。
- 正式上线前需要加鉴权、限流和日志脱敏（PRD 2.4、2.5），Demo 没有做。
