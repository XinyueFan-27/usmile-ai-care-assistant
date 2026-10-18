"""步骤 ⑩：权威口腔科普原文存档（不提交）。

用法：.venv/bin/python src/kb_fetch_authority.py
输出：data/processed/kb_raw/authority/<名称>.txt，第一行是来源链接和抓取日期。
PDF 用 pypdf 提取文字；网页只保留正文文字。写进 kb/ 的只是短摘录和自己整理的要点。
"""
import datetime
import gzip
import re
import urllib.request
from pathlib import Path

import pypdf

from kb_fetch_official import Text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "kb_raw" / "authority"
WEB = {
    "cdc_wuqu_2026": "https://www.chinacdc.cn/jkkp/mxfcrb/kqjk/202603/t20260323_315840.html",
    "cdc_qingshaonian": "https://www.chinacdc.cn/jkkp/mxfcrb/kqjk/202408/t20240823_295142.html",
    "jkzg_chuxue_2026": "https://m.gmw.cn/2026-09/24/content_1304567611.htm",
    "bj2yy_shuaya_2026": "https://m.gmw.cn/2026-09/20/content_1304565809.htm",
}
PDF = {
    "nhc_aiyari_2026": ("https://www.nhc.gov.cn/ylyjs/gzdt/202609/a5d831441714460fb70d96791abd0553/files/"
                        "3.2026%E5%B9%B4%E5%85%A8%E5%9B%BD%E7%88%B1%E7%89%99%E6%97%A5%E9%87%8D%E7%82%B9%E4%BA%BA%E7%BE%A4"
                        "%E5%8F%A3%E8%85%94%E5%81%A5%E5%BA%B7%E6%A0%B8%E5%BF%83%E4%BF%A1%E6%81%AF.pdf", "nhc_2026_aiyari_core.pdf"),
    "cma_wohd24": ("https://www.cndent.com/wp-content/uploads/2024/02/WOHD24-%E6%A0%B8%E5%BF%83%E4%BF%A1%E6%81%AF%E5%8D%A1"
                   "-%E5%8F%A3%E8%85%94-pb.pdf", "cma_wohd24.pdf"),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    for name, url in WEB.items():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=30).read()
        if raw[:2] == b"\x1f\x8b":  # 部分网站即使不请求也返回 gzip
            raw = gzip.decompress(raw)
        html = raw.decode("utf-8", "ignore")
        p = Text()
        p.feed(html)
        text = re.sub(r"\n{2,}", "\n", "\n".join(p.parts))
        (OUT / f"{name}.txt").write_text(f"来源：{url}  抓取：{today}\n{text}", encoding="utf-8")
        print(name, len(text))
    for name, (url, local) in PDF.items():
        path = OUT / local  # PDF 已在抓取时存到本地（不提交）
        text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
        (OUT / f"{name}.txt").write_text(f"来源：{url}  抓取：{today}\n{text}", encoding="utf-8")
        print(name, len(text))


if __name__ == "__main__":
    main()
