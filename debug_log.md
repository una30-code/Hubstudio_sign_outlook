# 调试与排障日志（Debug Log）

> 记录已遇到问题、根因、修复或规避方式，避免重复踩坑。勿写入真实账号、Cookie、Token、完整代理串。

## 使用约定

- 每条记录建议包含：**现象**、**环境**、**根因**、**处理**、**关联日期 / commit**（如有）
- 敏感信息脱敏或仅描述类型（如「某环境变量未加载」）

---

## 记录

### 2026-04-02 · phase-2 CDP 连接 ECONNREFUSED

- **现象**：执行 `python src/main.py --phase2` 后，流水线在 `step=connect_browser` 失败，错误为 `BrowserType.connect_over_cdp: WebSocket error: connect ECONNREFUSED 127.0.0.1:9222`。
- **环境**：Windows；Hubstudio connector 未在当前机器上监听对应 CDP 端口（或 `HUBSTUDIO_CDP_URL` 指向的 Browser GUID/端口与实际不一致）。
- **根因**：`connect_over_cdp` 时 WebSocket 端口未监听（拒绝连接），导致无法获取 `browser/context/page`。
- **处理**：
  - 检查并启动 `hubstudio_connector`，确保调试端点已启用；
  - 确认 `.env` 中 `HUBSTUDIO_CDP_URL` 的端口与当前实际一致；
  - 确认 Browser GUID 未变更后重跑 phase-2；
  - 若仍失败，将 `logs/phase2.log` 与失败截图（若有）补充记录。

---

### YYYY-MM-DD · 标题摘要

- **现象**：
- **环境**：
- **根因**：
- **处理**：

---
