# 部署到 Hugging Face Spaces（公开 Demo 链接）

> 个人作品集项目，非 usmile 官方，未上线。公开链接是网页演示，不是上线的小程序。

## 一次性准备（Melody 操作）

1. 在 Hugging Face 新建 Space：SDK 选 **Docker**（Blank 模板），硬件选免费的 **CPU basic**，可见性选 **Public**。
2. Space 页面 → **Settings → Variables and secrets → New secret**：名称 `ZHIPU_API_KEY`，值填智谱 Key。Key 只放在这里，不进任何文件。
3. 在 https://huggingface.co/settings/tokens 建一个 **Write** 权限的访问令牌（推送代码用，git 要求输入密码时填它）。

## 每次部署

在项目文件夹里运行（`<用户名>/<space 名>` 换成你的）：

```bash
git clone https://huggingface.co/spaces/<用户名>/<space 名> ../hf-space
deploy/huggingface/build_space.sh ../hf-space
cd ../hf-space && git add -A && git commit -m "部署 Demo" && git push
```

- `build_space.sh` 只复制运行需要的文件：`src/api.py`、`src/llm.py`、`src/core/`、`web/`、`kb/` 和本目录的 Dockerfile、README、requirements。不会复制 `data/`、`.env`、评测和分析脚本。复制完会检查有没有疑似密钥。
- 推送后 Space 会自动构建，第一次约 5–10 分钟（要装 CPU 版 torch 和下载 bge 模型）。构建日志在 Space 页面的 Logs。
- 链接：`https://huggingface.co/spaces/<用户名>/<space 名>`。免费 Space 一段时间没人访问会休眠，再打开时需要等几十秒启动。

## 限流（保护免费额度）

在 Dockerfile 里设了默认值，可在 Space 的 Settings → Variables 里改：

| 变量 | 默认 | 含义 |
|---|---|---|
| `DEMO_RATE_PER_MIN` | 6 | 每个访问者每分钟最多调用大模型几次 |
| `DEMO_DAILY_CAP` | 300 | 全站每天最多调用几次（北京时间） |

超出时，问答改为展示官方资料要点，并标明“演示额度”；推荐理由改用模板。页面照常可用。当前用量可在 `/api/health` 的 `quota` 里看到。本地开发和评测不设这两个变量，即不限。

## 部署前已验证（2026-10-19）

- 按 `build_space.sh` 组装的目录，用和容器相同的环境变量在本机启动：bge 检索、GLM 主备模型、首页都正常。
- 限流：每分钟 2 次时，同一访问者第 3 次提问切到“演示额度”模式，另一访问者不受影响。
- 依赖：Linux x86_64 下有 Python 3.13 的 torch 2.14.1 CPU 版和 faiss-cpu 1.15.1 安装包。
- 本机 Docker 没有启动，没有在本地做镜像构建；以 Space 的第一次构建日志为准。
