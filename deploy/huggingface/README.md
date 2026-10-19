---
title: usmile AI Care Assistant Demo
emoji: 🦷
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: 个人作品集项目，非 usmile 官方，未上线
---

> **个人作品集项目，非 usmile 官方需求，与 usmile 无合作关系，未上线。** 这是一个网页演示，不是上线的微信小程序。

# usmile AI 护齿助手 Demo

网页模拟微信小程序：售前 5 题定制选购（规则选型号，大模型只解释理由）+ 购后护齿问答（bge-small-zh 检索 + GLM 生成，回答带出处，医疗、售后、真伪、竞品问题按规则拒答或转向）。

- 完整项目（用户洞察、PRD、评测）：https://github.com/XinyueFan-27/usmile-ai-care-assistant
- 官方信息只来自知识库 `kb/`（品牌官方资料和权威口腔科普，带来源和日期），找不到的显示“待知识库”。
- 演示“App → 小程序数据同步”的一屏使用模拟设备数据，页面已标注“模拟设备数据，仅作演示，非真实用户”。
- 为保护免费额度，公开 Demo 限制了大模型调用次数（每人每分钟、全站每天）。超出时改为展示官方资料要点，并在页面上标明。
- 本助手提供的信息仅供参考，不能代替牙医诊断。
