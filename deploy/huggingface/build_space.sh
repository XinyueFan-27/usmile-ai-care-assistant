#!/usr/bin/env bash
# 把公开 Demo 需要的文件复制到 Hugging Face Space 的本地仓库目录。
# 用法：deploy/huggingface/build_space.sh <Space 仓库的本地路径>
# 只复制运行需要的代码、前端和知识库；不复制 data/、.env、评测、分析脚本。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${1:?请给出 Space 仓库的本地路径}"
[ -d "$DEST/.git" ] || { echo "$DEST 不是 git 仓库，请先 git clone 你的 Space"; exit 1; }

# 清掉旧文件（保留 .git 和 .gitattributes）
find "$DEST" -mindepth 1 -maxdepth 1 ! -name .git ! -name .gitattributes -exec rm -rf {} +

mkdir -p "$DEST/src"
cp "$ROOT/src/__init__.py" "$ROOT/src/api.py" "$ROOT/src/llm.py" "$DEST/src/"
rsync -a --exclude '__pycache__' "$ROOT/src/core" "$DEST/src/"
rsync -a --exclude '__pycache__' "$ROOT/web" "$ROOT/kb" "$DEST/"
cp "$ROOT/deploy/huggingface/Dockerfile" "$ROOT/deploy/huggingface/requirements.txt" "$ROOT/deploy/huggingface/README.md" "$DEST/"

# 安全检查：不允许带上密钥或原始数据
if grep -rIlE "ZHIPU_API_KEY=[^ \"'$]|[0-9a-f]{32}\.[A-Za-z0-9]{16}" "$DEST" --exclude-dir=.git; then
  echo "发现疑似密钥，已停止"; exit 1
fi
[ ! -e "$DEST/data" ] && [ ! -e "$DEST/.env" ] || { echo "发现 data/ 或 .env，已停止"; exit 1; }
echo "已复制到 $DEST："; (cd "$DEST" && find . -path ./.git -prune -o -type f -print | sort | sed 's/^/  /' | head -60)
