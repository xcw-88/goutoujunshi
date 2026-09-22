# 单 Worker 云端版

本目录是可选的 Cloudflare Workers 适配，不替换仓库根目录的 Codex Skill 或本地 Web/PWA。一个 Python Worker 提供 FastAPI API；同一个 Worker 的 Static Assets 提供 Next.js 静态前端。人物、关系、记忆和聊天文字在 D1；附件只随单次聊天请求处理，原文件不保存到云端。确认导入后，解析出的聊天文字会保存到 D1。没有 Pages、R2 或 KV 项目，也不需要电脑持续开机。

构建时 `scripts/sync_core.py` 从仓库原始 `SKILL.md`、`references/` 和后端纯请求模型/路由器复制内容到忽略的 `src/app/`；不要编辑生成目录。原 Skill 的独立记忆数据库和本地 Web 的 `data/` 不会自动迁移或被覆盖。

## 当前验证边界

- Python 3.14 适配测试、本地 D1 迁移和前端测试/静态构建用于本地验证。GitHub Actions 的 Linux `cloudflare` job 执行完整 Python 依赖打包与 dry-run；在本次无 R2 变更通过该检查前，不应正式部署。
- Windows 上 `uv` 创建 Pyodide 虚拟环境可能出错。可使用 Linux CI 打包产物中的 `python_modules/` 执行普通 `wrangler deploy --dry-run` 或部署；请先核对产物对应当前依赖锁文件和提交，且不要将生成目录提交到 Git。
- `/api/chat/stream` 保持 `meta`、`delta`、`done` SSE 事件，但目前等待模型完整响应后一次性发送 `delta`，不提供逐 token 反馈。

## 安全与数据

所有私人 `/api/` 路由都要求访问口令登录和由 `GOUTOU_SESSION_SECRET` 签名的 Secure、HttpOnly、SameSite=Strict Cookie。缺少口令或会话密钥时 API 拒绝服务。跨站写请求被拒绝。静态前端文件是公开的，但不包含私人数据；如需连登录页面都不可见，可额外配置 Cloudflare Access。不要把访问口令当作端到端加密。

`GOUTOU_API_KEY` 只能作为 Worker Secret 配置，设置页不能写入或清除此 Key。聊天正文和图片会发送到用户配置的模型服务商。前端 PWA 只缓存静态壳层，不缓存 API 数据。云端设置中，模型 URL 必须使用 HTTPS。

云端附件最多 8 个、合计最多 20 MB，其中图片合计最多 12 MB；文本上下文最多 10 万字符。附件可能被发送到所配置的模型服务商；本项目不保留原文件，不能在下次请求重用，重新生成时需重新选择原附件。旧版 `/api/files` 接口返回 HTTP 410。D1 仍会随聊天文字增长，应按需清理无用对话。免费 Worker 的 CPU/内存限制可能影响大文件处理，正式使用前应在目标账号测试并查看用量。中国大陆的实际访问取决于域名、运营商和网络环境，不保证所有地区可用。

## 在 Linux 或 Linux CI 中验证

需要 Node.js 22、Python 3.14 和 `uv`，并位于仓库根目录：

```sh
cd frontend && npm ci && npm test && npm run build:cloudflare
cd ../cloudflare && npm ci && uv run --python 3.14 python -m pytest
npm run deploy:dry
```

`deploy:dry` 不上传 Worker、不创建 D1，也不写远端数据。Windows 上的 `bundle:check` 要在 `python_modules/` 已由对应的 Linux CI 产物提供时才包含依赖验证。Linux CI 对 `deploy:dry` 的结果是正式部署前置条件。

## 手动部署清单（会修改你的 Cloudflare 账号）

只有你决定正式上线时才执行以下操作：

1. 在 `cloudflare/` 下用 `npx wrangler login` 登录你的账号。
2. 创建 D1 数据库 `goutoujunshi`：`npx wrangler d1 create goutoujunshi`。把 D1 返回的真实 `database_id` 填入本机 `wrangler.jsonc`，替换全零占位 UUID。**不要提交账号标识和敏感配置到公开仓库。** 不需要 R2 或 KV。
3. 在 Cloudflare Dashboard 或用 `npx wrangler secret put` 分别设置 `GOUTOU_ACCESS_PASSWORD`（高强度随机访问口令）、`GOUTOU_SESSION_SECRET`（至少 32 字符的独立随机值）和 `GOUTOU_API_KEY`。不要把值写在 `wrangler.jsonc`、`.dev.vars` 的提交中或命令行参数里。
4. 用 `npx wrangler d1 migrations apply goutoujunshi --remote` 初始化远端 D1（不要把 `--local` 误当远端）。
5. 确认 Linux `npm run deploy:dry` 成功，再运行 `npm run deploy`。这会发布一个 Worker 和同一 Worker 的静态资源；不会创建 Pages 项目。
6. 用手机打开部署 URL，验证口令登录、人物/记忆 CRUD、临时附件聊天、聊天记录导入和模型聊天。确认账单/额度、域名在目标网络的连通性，并准备 D1 备份策略。

不要将本地 `backend/.env`、`data/`、数据库、上传文件或原 Skill 记忆库提交到 Git。当前没有自动迁移本地私人数据到云端的流程。
