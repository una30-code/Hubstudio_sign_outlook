# 排障分析 → 结论写入 debug_log.md

## 提示词正文（复制以下）

```
请根据下面材料做排障分析。不要臆测我未提供的配置值；不确定写「需确认」。

本项目上下文：Playwright `connect_over_cdp` 连 Hubstudio；流水线步骤 `connect_browser` → `open_signup_page` → `verify_page`；结构化结果里常有 `step`、`success`、`message`、`screenshot_path`。

材料：
- 现象：【界面或返回值描述】
- 失败时的 `step`（若有）：【如 open_signup_page】
- 日志片段：【从 `logs/` 复制，脱敏】
- 报错栈或 Playwright 报错：【粘贴】
- 截图：【`screenshots/` 下文件名或文字描述页面】

请输出：
1. 最可能根因 Top 3，每条附简短验证步骤。
2. 建议修改位置（若能从仓库推断文件/函数名则写出）。
3. 一段可直接粘贴到 `debug_log.md` 的 Markdown（脱敏，日期用 YYYY-MM-DD）。
4. 若信息不足，列出最少补充项。

勿在回复中包含真实 CDP 地址全文或账号信息。
```
