"""步骤 ⑩：核对 kb/ 里「」原文摘录是否能在存档原文中逐字找到。

用法：.venv/bin/python src/kb_check_quotes.py
比对范围：data/processed/kb_raw/ 下的官网正文、权威科普文字、京东规格表和 OCR 结果。
比对时去掉空白字符。OCR 有错字时找不到，需要对照原图人工核对，结果写在 docs/METHODS.md。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "processed" / "kb_raw"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main() -> None:
    corpus = norm("\n".join(p.read_text(encoding="utf-8") for p in RAW.rglob("*.txt")))
    total, missing = 0, []
    for md in sorted((ROOT / "kb").rglob("*.md")):
        for q in re.findall(r"「([^」]+)」", md.read_text(encoding="utf-8")):
            if q in ("……",):
                continue
            total += 1
            if norm(q) not in corpus:
                missing.append((md.relative_to(ROOT), q))
    print(f"摘录 {total} 条，存档中逐字找到 {total - len(missing)} 条，未找到 {len(missing)} 条")
    for f, q in missing:
        print(f"  {f}: 「{q}」")


if __name__ == "__main__":
    main()
