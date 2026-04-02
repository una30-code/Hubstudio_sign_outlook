# 测试用例 → test.md

## 提示词正文（复制以下）

```
请为本项目更新或补全 `test.md`（默认只改测试文档，不写自动化代码，除非我明确要求）。

覆盖要与当前阶段一致：Hubstudio 已可通过 CDP 连接；验证「打开 Outlook 注册页且 URL 与注册相关元素同时成立」；失败有日志且失败截图在根目录 `screenshots/`；结构化结果字段含 `success`、`step`、`message`、`data`、`error`、`screenshot_path`。

请输出：
1. 用例表：ID、名称、前置条件、步骤摘要、期望结果（可客观判定）。
2. 至少包含：连接成功（对 `connect_browser`）、打开注册页（对 `open_signup_page`）、DOM+URL 校验（对 `verify_page`）、端到端成功、连接/导航失败负例（`success=False`、不崩溃）。
3. 说明 `test-results/` 与 `logs/`、`screenshots/` 的分工。

若现有 `test.md` 已有表格，在其基础上增量修改并更新变更记录小节。

额外说明（可选）：
【手工验收 / pytest / 是否必须真连 Hubstudio】
```
