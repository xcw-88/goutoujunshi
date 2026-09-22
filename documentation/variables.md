# 变量、配置与秘密

## 当前状态

原 Codex Skill 不需要 API 密钥。Web/PWA 的模型调用使用用户提供的 OpenAI-compatible 配置；API Key 只从环境变量或后端进程内存读取，不写入 SQLite。长期记忆 CLI 默认使用操作系统用户数据目录；测试或高级用户可以覆盖目录。

| 名称 | 使用者 | 作用域 | 来源 | 轮换 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `GOUTOUJUNSHI_MEMORY_DIR` | `scripts/memory_store.py` | 可选、本机 | 用户环境 | 不适用 | 指向私密本地目录；不得设为仓库或公共同步目录 |
| `GOUTOU_API_BASE` | Web 后端 | 可选、本机 | `backend/.env` 或环境 | 随服务商变更 | 只应指向用户信任的兼容接口 |
| `GOUTOU_API_KEY` | Web 后端 | 可选、本机 | `backend/.env`、环境或设置页进程内存 | 按服务商要求 | 不得提交、记录或由 API 原样返回 |
| `GOUTOU_MODEL` | Web 后端 | 可选、本机 | `backend/.env` 或设置页 | 不适用 | 模型必须与接口能力匹配；图片需要 vision |
| `GOUTOU_TEMPERATURE` | Web 后端 | 可选、本机 | `backend/.env` 或设置页 | 不适用 | 范围 0–2 |
| `GOUTOU_MAX_TOKENS` | Web 后端 | 可选、本机 | `backend/.env` 或设置页 | 不适用 | 范围 1–32768 |
| `GOUTOU_DATABASE_PATH` | Web 后端 | 可选、本机 | `backend/.env` 或环境 | 不适用 | 默认 `data/app.db`，不得提交 Git |
| `GOUTOU_UPLOAD_DIR` | Web 后端 | 可选、本机 | `backend/.env` 或环境 | 不适用 | 默认 `data/uploads`，包含私人文件 |

## 发布检查

- 确认仓库中没有聊天导出、截图、用户档案、邮箱、电话号码或本地账号信息。
- 确认没有令牌、Cookie、设备码、私钥或`.env`文件。
- 确认参考资料只包含公开来源或有权分发的原创整理内容。
- 若未来加入外部服务，把所有秘密限制在服务端或宿主安全存储，不写入Skill、README、工作流日志或示例。
