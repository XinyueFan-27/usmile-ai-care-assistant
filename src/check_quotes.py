"""核对文档里「」引用是否为评论或提问原文（铁律 8）。

用法：.venv/bin/python src/check_quotes.py docs/PRD_v1.0.md [更多文件]
规则：每个「…」后面必须紧跟 (Rxxx) 或 (Qxxx)；
R 对照 data/processed/reviews_clean.csv 的 full_text，
Q 对照 data/raw/京东商品问答_118条.csv 的 question（编号按 qa_tagged.csv 的 qa_id）。
引文必须是对应原文的子串。只打印编号和结果，不打印原文全文。
"""
import re
import sys

import pandas as pd

reviews = pd.read_csv("data/processed/reviews_clean.csv").set_index("review_id")["full_text"].astype(str)
raw_q = pd.read_csv("data/raw/京东商品问答_118条.csv")["question"].astype(str)
qa = pd.read_csv("data/processed/qa_tagged.csv").set_index("qa_id")["question"].astype(str)

# qa_tagged 的编号要和原始问答文件逐行一致
assert len(qa) == len(raw_q) and (qa.values == raw_q.values).all(), "qa_tagged 与原始问答不一致"

QUOTE = re.compile(r"「([^」]+)」\s*\((R\d{3}|Q\d{3})\)")
ANY = re.compile(r"「[^」]+」")

errors = 0
total = 0
for path in sys.argv[1:]:
    text = open(path, encoding="utf-8").read()
    matched_spans = set()
    for m in QUOTE.finditer(text):
        total += 1
        quote, rid = m.group(1), m.group(2)
        matched_spans.add(m.start())
        source = reviews.get(rid) if rid[0] == "R" else qa.get(rid)
        if source is None:
            print(f"✗ {path}: {rid} 编号不存在")
            errors += 1
        elif quote not in source:
            print(f"✗ {path}: {rid} 引文不是原文子串：{quote[:20]}…")
            errors += 1
    for m in ANY.finditer(text):
        if m.start() not in matched_spans:
            print(f"✗ {path}: 引号后没有编号：{m.group(0)[:20]}…")
            errors += 1

print(f"共核对 {total} 条引用，错误 {errors} 条")
sys.exit(1 if errors else 0)
