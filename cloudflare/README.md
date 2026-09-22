# 单 Worker 云端版（尚未部署）

本目录是可选的 Cloudflare Workers 适配，不替换仓库根目录的 Codex Skill 或本地 Web/PWA。一个 Python Worker 提供 FastAPI API；同一个 Worker 的 Static Assets 提供 Next.js 静态前端。人物、关系、记忆、会话及文件元数据在 D1，上传文件内容在 R2。没有 Pages 项目，也不需要电脑持续开机。

构建时 `scripts/sync_core.py` 从仓库原始 `SKILL.md`、`references/` 和后端纯请求模型/路由器复制内容到忽略的 `src/app/`；不要编辑生成目录。原 Skill 的独立记忆数据库和本地 Web 的 `data/` 不会自动迁移或被覆盖。

## 当前验证边界

- Python 3.14 下的 14 个适配测试、本地 D1 迁移、前端测试/静态构建以及 Wrangler 源码/绑定 dry-run 已通过。
- **普通 `wrangler deploy --dry-run` 不能验证 Python 依赖**：`fastapi`、Pydantic 等由 `pywrangler sync` 打包。必须使用 `npm run deploy:dry` 或 `npm run deploy`，不可直接拿 `bundle:check` 的成功当成可运行证明。
- 此 Windows 环境的 `uv` 在创建 Pyodide 虚拟环境时出错，因此这里没有通过 Worker 实际启动或含依赖的 dry-run。GitHub Actions 的 Linux `cloudflare` job 会执行该验证；在其成功前，部署兼容性仍未最终确认。
- `/api/chat/stream` 保持 `meta`、`delta`、`done` SSE 事件，但目前等待模型完整响应后一次性发送 `delta`，不提供逐 token 反馈。

## 安全与数据

所有私人 `/api/` 路由都要求访问口令登录和由 `GOUTOU_SESSION_SECRET` 签名的 Secure、HttpOnly、SameSite=Strict Cookie。缺少口令或会话密钥时 API 拒绝服务。跨站写请求被拒绝。静态前端文件是公开的，但不包含私人数据；如需连登录页面都不可见，可额外配置 Cloudflare Access。不要把访问口令当作端到端加密。

`GOUTOU_API_KEY` 只能作为 Worker Secret 配置，设置页不能写入或清除此 Key。聊天正文和图片会发送到用户配置的模型服务商。前端 PWA 只缓存静态壳层，不缓存 API 数据。云端设置中，模型 URL 必须使用 HTTPS。

云端聊天图片合计最多 12 MB（上传仍为每文件 20 MB）。Python Workers、D1、R2 都有各自的额度与限制，尤其免费 Worker CPU 时间不保证复杂聊天/大文件处理稳定；正式使用前应在目标账号测试并查看用量。中国大陆的实际访问取决于域名、运营商和网络环境，不保证所有地区可用。

## 在 Linux 或 Linux CI 中验证

需要 Node.js 22、Python 3.14 和 `uv`，并位于仓库根目录：

```sh
cd frontend && npm ci && npm test && npm run build:cloudflare
cd ../cloudflare && npm ci && uv run --python 3.14 python -m pytest
npm run deploy:dry
```

`deploy:dry` 不上传 Worker、不创建 D1/R2，也不写远端数据。Windows 上可运行 `npm run bundle:check` 检查源码、静态资源和绑定声明，但它不打包 Python 依赖。Linux CI 对 `deploy:dry` 的结果才是下一步部署前置条件。

## 手动部署清单（会修改你的 Cloudflare 账号）

只有你决定正式上线时才执行以下操作；本实施任务没有执行这些命令：

1. 在 `cloudflare/` 下用 `npx wrangler login` 登录你的账号。
2. 创建 D1 数据库 `goutoujunshi` 和私有 R2 存储桶 `goutoujunshi-uploads`：`npx wrangler d1 create goutoujunshi`、`npx wrangler r2 bucket create goutoujunshi-uploads`。把 D1 返回的真实 `database_id` 填入 `wrangler.jsonc`，替换全零占位 UUID。**不要提交账号标识和敏感配置到公开仓库。**
3. 在 Cloudflare Dashboard 或用 `npx wrangler secret put` 分别设置 `GOUTOU_ACCESS_PASSWORD`（高强度随机访问口令）、`GOUTOU_SESSION_SECRET`（至少 32 字符的独立随机值）和 `GOUTOU_API_KEY`。不要把值写在 `wrangler.jsonc`、`.dev.vars` 的提交中或命令行参数里。
4. 用 `npx wrangler d1 migrations apply goutoujunshi --remote` 初始化远端 D1（不要把 `--local` 误当远端）。
5. 确认 Linux `npm run deploy:dry` 成功，再运行 `npm run deploy`。这会发布一个 Worker 和同一 Worker 的静态资源；不会创建 Pages 项目。
6. 用手机打开部署 URL，验证口令登录、人物/记忆 CRUD、文件上传/读取/删除和模型聊天。确认账单/额度、域名在目标网络的连通性，并准备 D1/R2 备份策略。

不要将本地 `backend/.env`、`data/`、数据库、上传文件或原 Skill 记忆库提交到 Git。当前没有自动迁移本地私人数据到云端的流程。
