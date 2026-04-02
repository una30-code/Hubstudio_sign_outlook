# 设计扩写或修订 → design.md

## 提示词正文（复制以下）

```
请在本仓库 `design.md` 中扩写或修订下面主题（默认只改设计文档，不写 `src/`，除非我明确说实现）。

撰写要求（与现有 Phase 1 风格一致）：
- 自包含：在同一文档内写清目标、成功判据、不做范围、模块职责、执行顺序、失败时日志与 `screenshots/`、统一返回字典各字段含义。
- Hubstudio：说明经 CDP WebSocket 由 `connect_over_cdp` 接入；具体端口从环境变量读，不写死秘密。
- 模块边界：三步骤命名 `connect_browser`、`open_signup_page`、`verify_page`；编排层职责；建议 `src/` 文件名（`config.py`、`pipeline.py`、`main.py` 等）。
- 配置：列出 `.env` 键名表（如 `HUBSTUDIO_CDP_URL`、`OUTLOOK_REGISTER_URL`、`PAGE_LOAD_TIMEOUT_MS` 等）。
- `Page` 对象不塞进可序列化的 `data`；需要可选返回时在文档中说明「字典 + Page」并列 API。
- 风险与变更记录表格。

本次要我设计或修改的主题：
【例如：增加 Phase 2 子流程 / 调整 URL 判定规则 / 新增环境变量】

已知约束：
【例如：必须保持 URL+元素双校验 / 某 Hubstudio 版本行为】
```
