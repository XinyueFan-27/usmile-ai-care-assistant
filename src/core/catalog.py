"""型号属性表（kb/model_attributes.csv，由知识库步骤 ⑩ 生成和维护）。

推荐规则、按型号分流、首次设置、刷头提醒都只从这张表取型号信息。
- 文件不存在 → 型号信息都显示【待知识库】，推荐和分流如实返回“待知识库”。
- 字段为空、写着【待核实】或“未提及” → 显示【待知识库】，不参与打分，不推断（D38）。
- 每个字段 xxx 的出处在 xxx_src 列（来源编号，见 kb/sources.md）。
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import MODEL_ATTRIBUTES_CSV, PENDING, UNVERIFIED_MARKS

NOT_MENTIONED = "未提及"


def is_unverified(value) -> bool:
    v = "" if value is None else str(value).strip()
    return v == "" or v == NOT_MENTIONED or any(m in v for m in UNVERIFIED_MARKS)


def is_yes(value: str) -> bool:
    return value.startswith("是")


@dataclass
class ModelInfo:
    raw: dict

    def get(self, key: str) -> str:
        """取字段原值；没有依据时返回【待知识库】。"""
        v = self.raw.get(key)
        return PENDING if is_unverified(v) else str(v).strip()

    def src(self, key: str) -> list[str]:
        v = self.raw.get(f"{key}_src") or ""
        return [s for s in re.split(r"[;；,，\s]+", v) if s]

    @property
    def name(self) -> str:
        return self.get("model")

    @property
    def category(self) -> str:
        return self.get("category")

    @property
    def price(self) -> float | None:
        m = re.search(r"\d+(?:\.\d+)?", self.get("jd_list_price"))
        return float(m.group()) if m else None

    @property
    def app_status(self) -> str:
        """smart = 支持笑容加 App；basic = 官方确认不支持；unknown = 待核实。"""
        v = self.get("app_support")
        if v == PENDING:
            return "unknown"
        if v.startswith("否") or v.startswith("不"):
            return "basic"
        if is_yes(v) or v.startswith("支持"):
            return "smart"
        return "unknown"

    @property
    def replace_months(self) -> int | None:
        m = re.search(r"\d+", self.get("head_replace_months"))
        return int(m.group()) if m else None

    def facts_text(self) -> str:
        """所有有依据的字段拼起来，用来校验推荐理由里的数字和型号名。"""
        return " ".join(str(v) for k, v in self.raw.items() if not k.endswith("_src") and not is_unverified(v))


@dataclass
class Catalog:
    models: list[ModelInfo]
    available: bool  # 属性表是否存在
    path: str

    def find(self, name: str | None) -> ModelInfo | None:
        if not name:
            return None
        key = name.replace(" ", "").lower()
        return next((m for m in self.models if m.name.replace(" ", "").lower() == key), None)

    def names(self) -> list[str]:
        return [m.name for m in self.models if m.name != PENDING]


def load_catalog(path: Path | str = MODEL_ATTRIBUTES_CSV) -> Catalog:
    path = Path(path)
    if not path.exists():
        return Catalog([], False, str(path))
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("model") or "").strip() and not r["model"].startswith("#")]
    return Catalog([ModelInfo(r) for r in rows], True, str(path))
