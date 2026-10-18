"""步骤 ⑩：下载京东商品详情页图片并 OCR 成文字（只供人工核对，不直接入库）。

用法：.venv/bin/python src/kb_ocr.py <型号> <图片URL清单.txt>
输出：data/processed/kb_raw/img/<型号>/NN.jpg 与 data/processed/kb_raw/ocr_<型号>.txt（不提交）
OCR 用 rapidocr_onnxruntime（本地运行，不联网）。OCR 结果必须人工对照原图核对后才能写进 kb/。
"""
import sys
import urllib.request
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "processed" / "kb_raw"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://item.jd.com/"}


def download(url: str, path: Path) -> None:
    if path.exists():
        return
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        path.write_bytes(r.read())


def ocr_lines(engine: RapidOCR, path: Path) -> list[str]:
    result, _ = engine(str(path))
    if not result:
        return []
    # 按纵坐标分行，同一行按横坐标排序
    boxes = sorted(result, key=lambda b: (round(b[0][0][1] / 20), b[0][0][0]))
    return [b[1] for b in boxes if float(b[2]) > 0.5]


def main() -> None:
    model, url_file = sys.argv[1], Path(sys.argv[2])
    urls = [u.strip() for u in url_file.read_text().splitlines() if u.strip()]
    img_dir = RAW / "img" / model
    img_dir.mkdir(parents=True, exist_ok=True)
    engine = RapidOCR()
    out = []
    for i, url in enumerate(urls, 1):
        ext = ".png" if url.endswith(".png") else ".jpg"
        path = img_dir / f"{i:02d}{ext}"
        download(url, path)
        out.append(f"===== 图 {i:02d}  {url}")
        out.extend(ocr_lines(engine, path))
    (RAW / f"ocr_{model}.txt").write_text("\n".join(out), encoding="utf-8")
    print(f"{model}: {len(urls)} 张图，OCR {sum(1 for l in out if not l.startswith('====='))} 行")


if __name__ == "__main__":
    main()
