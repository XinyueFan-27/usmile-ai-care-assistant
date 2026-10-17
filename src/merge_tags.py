"""D19：合并两轮打标签结果，保证每个字段都经过人工抽检。

- 标签、情感、generic、info_need、整体情感：用 v1.2.1 那一轮（第一批 50 条抽检 88% 通过）。
- claim_gap、ai_can_help：用 v1.3 那一轮（定义在 D18 更新，第二批 20 条抽检）。
- ai_can_help 规则：info_need 为 true 时一定为 true；generic 且无任何标签时为 false。

运行：.venv/bin/python src/merge_tags.py && .venv/bin/python src/tag.py --only reviews
（tag.py 发现全部已缓存，只重建输出文件，不调用模型。）
"""

import json
from pathlib import Path

PROC = Path(__file__).resolve().parents[1] / "data/processed"
BASE = PROC / "tag_cache_reviews_llm_v121.jsonl"
NEW = PROC / "tag_cache_reviews_llm_v13.jsonl"
OUT = PROC / "tag_cache_reviews_llm.jsonl"


def load(p: Path) -> dict:
    return {r["id"]: r for r in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())}


def main() -> None:
    base, new = load(BASE), load(NEW)
    missing = set(base) ^ set(new)
    if missing:
        raise SystemExit(f"两轮条目不一致：{sorted(missing)}")
    merged = []
    for rid, b in base.items():
        n = new[rid]
        has_tags = bool(b["tags"] or b["non_product_tags"])
        ai = (bool(n.get("ai_can_help")) or b["info_need"]) and not (b["generic"] and not has_tags)
        merged.append({**b, "claim_gap": n["claim_gap"], "ai_can_help": ai,
                       "source": "v1.2.1 + v1.3(claim_gap, ai_can_help)"})
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in merged), encoding="utf-8")
    print(f"合并 {len(merged)} 条 → {OUT.name}；claim_gap {sum(r['claim_gap'] for r in merged)}，"
          f"ai_can_help {sum(r['ai_can_help'] for r in merged)}，info_need {sum(r['info_need'] for r in merged)}")


if __name__ == "__main__":
    main()
