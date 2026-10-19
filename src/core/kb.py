"""读取 kb/ 下的知识块和来源清单。

知识块格式见 kb/README.md：每块以「### 编号 标题」开头，下面是
「- 适用 / 来源 / 来源级别 / 抓取日期 / 类型」5 行元信息，再接“要点”和“原文摘录”。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .config import KB_DIR

SKIP_FILES = {"README.md", "sources.md"}
HEAD = re.compile(r"^###\s+(\S+)\s+(.*)$")
META = re.compile(r"^-\s*(适用|来源|来源级别|抓取日期|类型)：\s*(.*)$")
SOURCE_ID = re.compile(r"\b([SA]\d{2})\b")


@dataclass
class Chunk:
    chunk_id: str
    title: str
    path: str  # 相对 kb/ 的路径
    meta: dict = field(default_factory=dict)
    body: str = ""

    @property
    def applies_to(self) -> str:
        return self.meta.get("适用", "")

    @property
    def summary(self) -> str:
        """“要点”一段；没有就用正文前 200 字。"""
        m = re.search(r"要点：(.*?)(?:\n原文摘录：|\Z)", self.body, re.S)
        return (m.group(1) if m else self.body[:200]).strip()

    @property
    def source_ids(self) -> list[str]:
        return list(dict.fromkeys(SOURCE_ID.findall(self.meta.get("来源", ""))))

    def search_text(self) -> str:
        return f"{self.title}\n适用：{self.applies_to}\n{self.body}"


def parse_markdown(text: str, rel_path: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur: Chunk | None = None
    body: list[str] = []

    def flush():
        if cur is not None:
            cur.body = "\n".join(body).strip()
            chunks.append(cur)

    for line in text.splitlines():
        h = HEAD.match(line)
        if h:
            flush()
            cur, body = Chunk(h.group(1), h.group(2).strip(), rel_path), []
            continue
        if cur is None:
            continue
        if line.startswith("## ") or line.startswith("# "):
            flush()
            cur, body = None, []
            continue
        m = META.match(line)
        if m and not body:
            cur.meta[m.group(1)] = m.group(2).strip()
        elif not line.startswith(">"):
            body.append(line)
    flush()
    return chunks


def load_chunks(kb_dir: Path = KB_DIR) -> list[Chunk]:
    if not kb_dir.exists():
        return []
    out: list[Chunk] = []
    for p in sorted(kb_dir.rglob("*.md")):
        if p.name in SKIP_FILES:
            continue
        out.extend(parse_markdown(p.read_text(encoding="utf-8"), str(p.relative_to(kb_dir))))
    return out


def load_sources(kb_dir: Path = KB_DIR) -> dict[str, dict]:
    """解析 sources.md 里的表格行：| S01 | 名称 | 链接 | ... |"""
    path = kb_dir / "sources.md"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"[SA]\d{2}", cells[0]):
            link = next((u for u in re.findall(r"https?://[^\s|）)]+", line)), "")
            out[cells[0]] = {"id": cells[0], "name": cells[1], "url": link}
    return out


@lru_cache(maxsize=1)
def default_chunks() -> tuple[Chunk, ...]:
    return tuple(load_chunks())


@lru_cache(maxsize=1)
def default_sources() -> dict:
    return load_sources()


def chunk_by_id(chunk_id: str, chunks=None) -> Chunk | None:
    for c in chunks if chunks is not None else default_chunks():
        if c.chunk_id == chunk_id:
            return c
    return None


def citation(chunk: Chunk, sources: dict | None = None) -> dict:
    """把知识块转成界面能显示的出处：知识块编号 + 来源名称和链接。"""
    sources = default_sources() if sources is None else sources
    refs = [sources.get(s, {"id": s, "name": s, "url": ""}) for s in chunk.source_ids]
    return {
        "chunk_id": chunk.chunk_id,
        "title": chunk.title,
        "file": f"kb/{chunk.path}",
        "fetched": chunk.meta.get("抓取日期", ""),
        "level": chunk.meta.get("来源级别", ""),
        "sources": refs,
    }
