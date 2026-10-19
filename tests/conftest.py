"""测试用假数据：tests/fixtures/ 下的型号、参数、来源编号（T01 等）全部是编的，
只用来测规则逻辑；不得出现在 Demo 界面和评测结果里。"""

import os
from pathlib import Path

# 测试不联网、不调大模型：固定用备用检索 + mock
os.environ.setdefault("RAG_RETRIEVER", "tfidf")
os.environ.setdefault("DEMO_FORCE_MOCK", "1")

import pytest

from src.core.catalog import load_catalog
from src.core.kb import parse_markdown
from src.core.retriever import TfidfIndex

FIXTURES = Path(__file__).parent / "fixtures"

# 测试用假数据：知识块格式与 kb/README.md 一致，内容是编的
FAKE_KB = """# 测试用假数据
### T-KB-01 测试型号A 续航
- 适用：测试型号A
- 来源：T01
- 来源级别：1 品牌官方
- 抓取日期：2026-10-18
- 类型：参数

要点：测试型号A 续航测试数值，测试用假数据。

### T-KB-02 测试刷头更换
- 适用：通用
- 来源：T02
- 来源级别：1 品牌官方
- 抓取日期：2026-10-18
- 类型：使用建议

要点：测试刷头更换周期说明，测试用假数据。
"""


@pytest.fixture
def fake_catalog():
    return load_catalog(FIXTURES / "fake_model_attributes_测试用假数据.csv")


@pytest.fixture
def fake_chunks():
    return parse_markdown(FAKE_KB, "test/fake.md")


@pytest.fixture
def fake_index(fake_chunks):
    return TfidfIndex(fake_chunks)
