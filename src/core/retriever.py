"""知识库检索。

- 首选：本地 bge-small-zh（BAAI/bge-small-zh-v1.5）向量化 + FAISS 内积检索。
- 备用：没装 sentence-transformers / faiss 时，用字符二元组 TF-IDF（纯 numpy），
  界面和结果里会注明“关键词检索（备用）”，评测时以 bge 版为准。
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from .kb import Chunk, default_chunks

BGE_MODEL = os.getenv("BGE_MODEL", "BAAI/bge-small-zh-v1.5")
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
# 低于这个相似度就当作“没有找到可靠资料”；第 ⑫ 步按评测结果再调
THRESHOLD = {"bge": float(os.getenv("RAG_MIN_SCORE_BGE", 0.38)),
             "tfidf": float(os.getenv("RAG_MIN_SCORE_TFIDF", 0.10))}


def _grams(text: str) -> list[str]:
    t = re.sub(r"\s+", "", text.lower())
    return [t[i:i + 2] for i in range(len(t) - 1)]


class TfidfIndex:
    kind = "tfidf"
    label = "关键词检索（备用）"

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        docs = [Counter(_grams(c.search_text())) for c in chunks]
        df = Counter(g for d in docs for g in d)
        n = len(docs)
        self.idf = {g: math.log((n + 1) / (v + 1)) + 1 for g, v in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, counts: Counter) -> dict:
        v = {g: c * self.idf.get(g, 0.0) for g, c in counts.items() if g in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {g: x / norm for g, x in v.items()}

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        q = self._vec(Counter(_grams(query)))
        scores = [sum(w * d.get(g, 0.0) for g, w in q.items()) for d in self.vecs]
        order = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


class BgeIndex:
    kind = "bge"
    label = "bge-small-zh 向量检索"

    def __init__(self, chunks: list[Chunk]):
        import faiss  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self.chunks = chunks
        self.model = SentenceTransformer(BGE_MODEL)
        emb = self.model.encode([c.search_text() for c in chunks], normalize_embeddings=True)
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(np.asarray(emb, dtype="float32"))

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        q = self.model.encode([BGE_QUERY_PREFIX + query], normalize_embeddings=True)
        scores, ids = self.index.search(np.asarray(q, dtype="float32"), k)
        return [(self.chunks[i], float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]


def bge_available() -> bool:
    try:
        import faiss  # noqa: F401, PLC0415
        import sentence_transformers  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


def build_index(chunks: list[Chunk], prefer: str = "auto"):
    if prefer in ("auto", "bge") and bge_available():
        try:
            return BgeIndex(chunks)
        except Exception:  # noqa: BLE001  模型没下载等情况，退回备用检索
            if prefer == "bge":
                raise
    return TfidfIndex(chunks)


@lru_cache(maxsize=1)
def default_index():
    return build_index(list(default_chunks()), os.getenv("RAG_RETRIEVER", "auto"))
