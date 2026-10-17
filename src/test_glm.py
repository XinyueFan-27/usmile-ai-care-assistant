"""GLM 连通测试：只打印模型回复，不打印 Key。

运行：.venv/bin/python src/test_glm.py
"""

from llm import chat

if __name__ == "__main__":
    print(chat([{"role": "user", "content": "请用一句话回复：连通测试成功。"}], temperature=0.1))
