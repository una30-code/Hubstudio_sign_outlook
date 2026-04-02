# 提示词目录（prompts）

本目录是可复制到 AI 对话的**提示模板**，面向本项目：**Hubstudio 指纹浏览器 + Playwright（CDP 连接）+ Outlook 注册页打开与校验（Phase 1）**。使用前打开对应 `.md`，复制「提示词正文」代码块，把 `【…】` 占位换成你的情况。

**Phase 1 代码脉络（便于选模板）**：`connect_browser` → `open_signup_page` → `verify_page`，由 `pipeline.py` 编排，`main.py` 入口；配置在 `config.py` + `.env`；失败截图在根目录 `screenshots/`，业务日志在 `logs/`。

| 文件 | 适用场景 |
|------|----------|
| [requirements_refine.md](./requirements_refine.md) | 把新目标写成可验收需求条目（改 `requirements.md`） |
| [design_feature.md](./design_feature.md) | 为新增能力扩写设计（改 `design.md`，不写代码除非另有说明） |
| [task_implement.md](./task_implement.md) | 只做 `tasks.md` 里**一条**任务（如 T-004～T-008） |
| [debug_analyze.md](./debug_analyze.md) | 根据日志/截图/报错排障，产出可写入 `debug_log.md` 的段落 |
| [test_cases.md](./test_cases.md) | 补全或调整 `test.md` 用例表 |
| [doc_sync.md](./doc_sync.md) | 代码变更后对齐 `tasks` / `design` / `test` / `debug_log` |
| [playwright_selectors.md](./playwright_selectors.md) | 针对 Outlook 注册相关页写稳定选择器与等待（需贴 DOM） |

**约定**：敏感信息脱敏或用「见本地 .env」；勿粘贴真实密码、Cookie、完整带鉴权 URL。
