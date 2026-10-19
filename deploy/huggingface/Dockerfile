# usmile AI 护齿助手 Demo（个人作品集项目，非 usmile 官方，未上线）
# Hugging Face Spaces（Docker 类型）用。大模型 Key 由作者在 Space 的 Settings → Secrets 里填 ZHIPU_API_KEY，不写进镜像。
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/user/.cache/huggingface

RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

# 先装 CPU 版 torch，避免装上几 GB 的 GPU 版
COPY --chown=user requirements.txt .
RUN pip install --user torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --user -r requirements.txt

# 构建时下载 bge-small-zh，运行时离线加载
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

COPY --chown=user . .

# 模型名（不是密钥）和公开 Demo 的限流设置；可在 Space 的 Settings → Variables 里覆盖
ENV HF_HUB_OFFLINE=1 \
    ZHIPU_MODEL=glm-4.7-flash \
    ZHIPU_FALLBACK_MODEL=glm-4-flash-250414 \
    ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4 \
    DEMO_RATE_PER_MIN=6 \
    DEMO_DAILY_CAP=300

EXPOSE 7860
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]
