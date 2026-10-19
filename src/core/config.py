"""全局常量：路径、占位文案、免责声明。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "kb"
MODEL_ATTRIBUTES_CSV = KB_DIR / "model_attributes.csv"

# 知识库里没有、或字段写着【待核实】时，界面一律显示这个占位，不编造
PENDING = "【待知识库】"
UNVERIFIED_MARKS = ("【待核实】", "待核实", "【待知识库】")

DISCLAIMER = "本助手提供的信息仅供参考，不能代替牙医诊断。"
FOOTER = "个人作品集项目，非 usmile 官方，未上线。"
SIMULATED_LABEL = "模拟设备数据，仅作演示，非真实用户"
MOCK_LABEL = "【mock 模式】未配置大模型 Key，以下是检索到的官方资料要点，未经大模型整理"
FALLBACK_LABEL = "【大模型暂时繁忙】以下是检索到的官方资料要点，未经大模型整理，可以稍后再问一次"
QUOTA_LABEL = "【演示额度】为保护免费额度，公开 Demo 限制了大模型调用次数，以下是检索到的官方资料要点，未经大模型整理，可以稍后再问"
KB_SUMMARY_LABEL = "【官方资料要点】大模型没有整理出可靠的回答，以下是检索到的相关官方资料，未经大模型整理"
