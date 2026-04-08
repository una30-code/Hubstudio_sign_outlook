# 术语表（Glossary）

> **职责**：集中解释本项目中出现的专业名词与缩写。业务「要什么」见 `requirements.md`；架构与边界见 `design.md`；配置键与冻结字段见 `docs/contracts.md`。

---

## 浏览器与自动化

| 术语 | 解释 |
| ---- | ---- |
| **CDP（Chrome DevTools Protocol）** | 浏览器对外暴露的调试协议。自动化工具通过 CDP 附着到**已在运行**的 Chromium 系浏览器，从而驱动页面，而不一定由脚本从零启动浏览器。 |
| **Playwright** | 微软开源的浏览器自动化库。本仓库在 phase-2 中用其 `connect_over_cdp` 连接 Hubstudio 启动的指纹浏览器。 |
| **`connect_over_cdp`** | Playwright 通过 CDP 端点（通常为 `http://127.0.0.1:<端口>` 或 `ws://...`）连接到现有浏览器进程的方式。 |
| **指纹浏览器 / 指纹环境** | 在独立配置（代理、UA、语言等）下运行的浏览器实例，用于降低多账号场景下的环境关联风险。本项目中由 **Hubstudio** 管理。 |
| **DOM** | 网页文档对象模型。自动化脚本通过选择器在 DOM 上定位元素并点击、输入。页面改版会导致 DOM 变化，选择器可能失效。 |
| **best-effort** | 「尽力而为」：执行某步（如先停再起浏览器）时，若中间非关键失败不阻断主流程；与「必须成功否则中止」相对。 |

---

## Hubstudio 相关

| 术语 | 解释 |
| ---- | ---- |
| **Hubstudio** | 第三方指纹浏览器与多环境管理产品。本仓库通过其 **本机 HTTP API**（如 `http://127.0.0.1:6873`）创建环境、启停浏览器会话。 |
| **`containerCode` / 环境 ID** | Hubstudio 为每个环境分配的数字（或文档中的等价标识）。phase-0 创建成功后得到，phase-2 启动浏览器、连接 CDP 时需要指向该 ID。代码与留档中也可能写作 `container_code`（蛇形命名）。 |
| **`containerName` / `environment_name`** | 环境的显示名称；本仓库有固定命名规则（网址名称 + 序号 + 地区 + 日期），见 `docs/contracts.md` §环境名称规则。 |
| **`debuggingPort`** | Hubstudio 在 `browser/start` 等接口返回的本地调试端口。用于拼出 CDP 的 HTTP 入口（如 `http://127.0.0.1:{debuggingPort}`），供 Playwright 连接。 |
| **Hubstudio HTTP API 与 CDP** | **HTTP API**：向 Hubstudio 进程发 REST 请求（创建环境、启停浏览器）。**CDP**：连接**已启动的浏览器内核**进行页面自动化。二者协议与用途不同，排障时需区分（例如 `ECONNREFUSED` 到某端口通常是 CDP 侧未监听）。 |

---

## 数据与工程约定

| 术语 | 解释 |
| ---- | ---- |
| **JSONL** | 每行一个独立 JSON 对象的文本格式，适合追加写入一条业务记录。本仓库 **archive 留档** 使用 JSONL。 |
| **archive（留档）** | 与「运行日志」区分：记录**业务结果**（如某次创建环境成功、`containerCode`、时间戳），便于后续 phase 读取与审计。目录一般为 `logs/archive/`。 |
| **`StepResult`** | 流水线每步统一的结构化返回：`success`、`step`、`message`、`data`、`error`、`screenshot_path` 等，定义见 `src/step_result.py` 与 `docs/contracts.md`。 |
| **`step`（字段）** | 标识当前失败或成功的**逻辑步骤名**（如 `connect_browser`、`apply_signup_profile`），用于日志与测试对齐，不等同于「需求 phase-0/1/2」编号。 |
| **phase-0 / phase-1 / phase-2** | **需求分阶段**：0 建 Hubstudio 环境；1 生成合成注册用户信息并留档；2 启动该环境、连 CDP、打开 Outlook 注册页并执行约定范围内的页面自动化。见 `requirements.md` §1。 |
| **合成身份** | phase-1 生成的姓名、生日、账号、密码等**用于填表与测试**，非真实证件信息；不表示已完成微软侧开户。 |
| **A 方案（序号）** | 环境名中序号由 `logs/sequence_state.json` 按「站点 + 地区 + 本地日期」维度自动递增，避免重复；`name_sequence_start` 仅用于纠偏或初始化。 |

---

## 测试与任务

| 术语 | 解释 |
| ---- | ---- |
| **冒烟测试** | 快速手工或脚本跑通主路径，确认无明显崩溃；不要求覆盖所有边界。 |
| **TC-Px-xxx** | `test.md` 中的用例编号，与 `tasks.md` 任务 ID 在 `docs/codemap.md` 中可追溯对应。 |

---

## 变更说明

新增或更名术语时，请只改本文件，避免在 `requirements.md` / `design.md` 重复写长段定义（可在正文首次出现处链到本节锚点）。
