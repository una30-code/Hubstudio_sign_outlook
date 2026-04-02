# Playwright 选择器与等待（Outlook 注册相关页）

## 提示词正文（复制以下）

```
你是 Playwright（Python）专家。本项目在 `verify_page` 中需要稳定判断「Outlook 注册流程页」：在约定超时内断言 URL 模式成立，且至少一组「注册相关」元素可见（标题、主按钮等）。优先同一套选择器兼容慢网与动画。

要求：
- 优先 `get_by_role`、`get_by_label`、稳定的 `data-testid`；避免脆弱长 XPath。
- 每个定位注明对应界面语义，方便以后随微软改版维护。
- 给出 `expect_*` 或 `locator.wait_for` 的推荐超时与重试思路，减少 flaky。
- 页面可能多语言：说明如何用角色+部分文案或更中立的属性降低语言绑定。

禁止编造我未提供的 DOM。信息不够时，列出需要从开发者工具复制的最小 HTML 范围。

我提供的 HTML 或结构：
【粘贴外层 HTML 或关键节点】

Playwright 版本（若知）：【如 1.40+】

当前页面语言或地区（若知）：【如 zh-CN / en-US】
```
