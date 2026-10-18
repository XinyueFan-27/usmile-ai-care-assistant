"""步骤 ⑩：抓取 usmile 官网（usmile.com/cn）公开页面的正文文字，存档备查（不提交）。

用法：.venv/bin/python src/kb_fetch_official.py
输出：data/processed/kb_raw/official/<名称>.txt，每个文件第一行是来源链接和抓取日期。
只做存档；写进 kb/ 的内容由人工从存档中摘录并核对。
"""
import datetime
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "kb_raw" / "official"
BASE = "https://www.usmile.com"
PAGES = {
    "download": "/cn/download",
    "aftersale": "/cn/aftersale",
    "buy": "/cn/buy",
    "electrictoothbrush": "/cn/electrictoothbrush",
    "childoralcavity": "/cn/childoralcavity",
    "accessories": "/cn/accessories",
    "head_lingdong3": "/cn/accessories/newinfo.html?id=38",
    "head_guanjie2": "/cn/accessories/newinfo.html?id=37",
    "head_qidian": "/cn/accessories/info.html?id=1",
    "head_kids": "/cn/accessories/newinfo.html?id=36",
}
MODELS = {"L30": 42, "F20": 33, "U7Pro": 29, "F10PRO": 19, "Y50": 44, "Y30Pro": 31, "Y30": 30,
          "Y20": 28, "P70": 41, "P20": 32, "P20PRO": 27, "P10PRO": 17}
KIDS = {"Q30": 35, "Q20Pro": 34, "Q20": 25}
for k, i in MODELS.items():
    PAGES[f"model_{k}"] = f"/cn/electrictoothbrush/newinfo.html?id={i}"
for k, i in KIDS.items():
    PAGES[f"model_{k}"] = f"/cn/childoralcavity/newinfo.html?id={i}"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    for name, path in PAGES.items():
        req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        p = Text()
        p.feed(html)
        text = re.sub(r"\n{2,}", "\n", "\n".join(p.parts))
        (OUT / f"{name}.txt").write_text(f"来源：{BASE + path}  抓取：{today}\n{text}", encoding="utf-8")
        print(name, len(text))


if __name__ == "__main__":
    main()
