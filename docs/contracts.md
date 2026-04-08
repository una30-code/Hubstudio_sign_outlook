# 契约与配置（Contracts）

> **职责说明**：本文件是所有“配置项、Hubstudio 请求字段映射、冻结数据结构定义、留档（archive）规范、phase-2 环境变量、以及 step 取值”的唯一权威说明。  
> 其中“冻结数据结构”指的是跨多个模块或对接时约定好、后续不能随意更改的数据结构（比如统一返回格式 StepResult、留档内容等），一旦约定后，后续开发和接口对接都要严格按照这里定义执行。  
> 换句话说：当你需要修改 `.env` 配置文件、对接阶段性产物、或者调整 API 请求与返回的数据结构时，**一定要以本文件为准**，以保证各方理解一致，避免因口径不一导致的对接和兼容性问题。
> **不包含**：为什么要这样做、范围外说明、排障故事——见 `design.md`；验收条文见 `requirements.md`。  
> **术语**：见 `docs/glossary.md`。

---

## 1. 统一返回结构 `StepResult`

与 `src/step_result.py` 中 `StepResult`（TypedDict）一致。

| 字段 | 类型 | 含义 |
| ---- | ---- | ---- |
| `success` | bool | 本步是否成功 |
| `step` | str | 逻辑步骤名（见 §8） |
| `message` | str | 人类可读说明 |
| `data` | object | 成功或补充信息（键随步骤变化） |
| `error` | str \| null | 失败时错误摘要 |
| `screenshot_path` | str \| null | 若有页面，失败时可能写入截图路径 |

phase-0 环境创建成功时，`data` 至少含：`container_code`、`environment_name`（与 Hubstudio 返回及命名规则一致）。

---

## 2. 留档（archive）约定

| 项 | 约定 |
| -- | ---- |
| 目录 | `logs/archive/` |
| 格式 | **JSONL**：一行一个 JSON 对象 |
| 与日志边界 | `logs/*.log` = 运行轨迹；`logs/archive/*.jsonl` = 业务结果留档 |
| 结果回传 | 调用结果宜含 `archive_path` 和/或 `archive_ref`（至少其一） |

### 2.1 文件命名

| phase | 文件名模式 |
| ----- | ---------- |
| phase-0 | `phase0_env_create_YYYYMMDD.jsonl` |
| phase-1 | `phase1_user_profile_YYYYMMDD.jsonl` |
| phase-2 | `phase2_signup_smoke_YYYYMMDD.jsonl`（成功路径写入时） |

### 2.2 phase-1 留档最小字段

`first_name`、`last_name`、`birth_date`、`account`、`generated_at`、`success`（以及实现若写入的 `password`：archive 可存明文，**日志仍须脱敏**）。

### 2.3 phase-2 成功留档载荷（摘要）

`phase=phase2_signup_smoke`；宜含：`container_code`（若有）、`used_cdp_url_override`、`current_url`、`url_ok` / `element_ok` / `element_hit`、`steps_completed`、`email_used`、`hold_challenge`（摘要）、`verified_at`；**不含密码**。

---

## 3. phase-0：Hubstudio 环境创建

### 3.1 运行配置（`.env`）

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
| ------ | ---- | ---- | ------ | ---- |
| `HUBSTUDIO_API_BASE` | string | 是 | 无 | Hubstudio API 根 URL，如 `http://127.0.0.1:6873` |
| `LOG_DIR` | string | 否 | `logs` | 运行日志目录 |
| `SCREENSHOTS_DIR` | string | 否 | `screenshots` | 失败截图目录 |

### 3.2 业务配置（`hubstudio_env_create_config`）

| 字段名 | 类型 | 必填 | 默认值 | 校验摘要 | 映射到 Hubstudio |
| ------ | ---- | ---- | ------ | -------- | ---------------- |
| `site_name` | string | 否 | `outlook` | 非空 | 参与命名，不直映射 |
| `region` | string | 是 | 无 | 非空 | 参与命名与校验 |
| `name_sequence_start` | int | 否 | `1` | 仅初始化/纠偏；常态由序号状态文件维护 | 不映射 |
| `environment_name` | string | 否 | 按规则生成 | 1–60 字，须符合命名规则 | `containerName` |
| `proxy.host` | string | 是 | 无 | 非空 | `proxyServer` |
| `proxy.port` | int | 是 | 无 | 1–65535 | `proxyPort` |
| `proxy.username` | string | 是 | 无 | 非空 | `proxyAccount` |
| `proxy.password` | string | 是 | 无 | 非空 | `proxyPassword` |
| `fingerprint.ua` | string | 否 | 见示例 | 非空 | `advancedBo.ua` |
| `fingerprint.ua_version` | string | 否 | `124.0.0.0` | 非空 | `advancedBo.uaVersion` |

### 3.3 请求体固定常量（不可由业务配置覆盖）

| 含义 | 值 | Hubstudio 字段 |
| ---- | -- | -------------- |
| 代理类型 | 仅 Socks5 | `proxyTypeName` |
| 平台 | `windows` | `type` |
| 浏览器 | `chrome` | `browser` |
| 内核版本 | `124` | `coreVersion` |
| 语言 | `["en", "en-US"]` | `advancedBo.languages` |
| 动态类型 | `1` | `asDynamicType` |

### 3.4 代理字符串兼容（可选）

| 字段名 | 规则 | 说明 |
| ------ | ---- | ---- |
| `proxy_raw` | `host:port:user:pass` | 提供代理配置信息的简便字符串格式，内容依次为主机、端口、用户名、密码。该字段与结构化的 `proxy.*` 字段只能二选一填写——如果两者同时存在，以结构化 `proxy.*` 字段为准。

### 3.5 创建接口与示例 JSON

- **接口**：`POST /api/v1/env/create`
- **示例请求体**（逻辑结构）：

```json
{
  "containerName": "outlook1_美国_2026年4月1日",
  "asDynamicType": 1,
  "proxyTypeName": "Socks5",
  "proxyServer": "161.77.3.187",
  "proxyPort": 12324,
  "proxyAccount": "example_user",
  "proxyPassword": "example_pass",
  "type": "windows",
  "browser": "chrome",
  "coreVersion": 124,
  "advancedBo": {
    "uaVersion": "124.0.0.0",
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "languages": ["en", "en-US"]
  }
}
```

### 3.6 环境名称规则（摘要）

- 自动生成格式：`{site_name}{effective_sequence}_{region}_{YYYY年M月D日}`（本地日历日期）。
- 序号由 `logs/sequence_state.json` 按 `site_name + region + 日期` 维护（A 方案）；批量创建时第 `k` 条使用 `next_sequence + k`。
- 显式 `environment_name` 须与上述语义一致且长度合规；超长按 Hubstudio 限制截断（实现与参考脚本对齐）。

### 3.7 phase-0 主流程 `step`

主流程为 `hubstudio_env_creation`（子步骤可为 `load_config` / `validate_config` / `api_env_create` 等实现约定字符串）。

---

## 4. phase-1：用户信息生成（冻结接口）

| 项 | 值 |
| -- | -- |
| 运行入口 | `python src/main.py --phase1` 或 `PHASE=1` |
| `StepResult.step` | **`outlook_user_profile`**（固定） |
| `StepResult.data` 键（固定） | `first_name`、`last_name`、`birth_date`（ISO `YYYY-MM-DD`）、`account`、`password` |
| 日志 | **禁止**输出完整 `password`（掩码或省略） |

字段规则：美国风格姓名；生日年龄 18–55 岁（含边界）；账号为规范化姓名 + 5 位随机数字；密码长度 10 且含数字、小写、大写。

---

## 5. phase-2：CDP、Hubstudio 启停与 `.env`

### 5.1 Hubstudio HTTP 与浏览器 CDP

| 能力 | 典型配置 | 用途 |
| ---- | -------- | ---- |
| Hubstudio HTTP | `HUBSTUDIO_API_BASE` | `env/create`；默认路径下 `browser/stop`（best-effort）+ `browser/start` |
| 浏览器 CDP | `http://127.0.0.1:{debuggingPort}` 或 `HUBSTUDIO_CDP_URL` | Playwright `connect_over_cdp` |

配置加载：`load_phase2_settings()`（`src/config.py`）。

### 5.2 phase-2 环境变量（`load_phase2_settings`）

| 字段名 | 默认路径下必填 | 说明 |
| ------ | -------------- | ---- |
| `HUBSTUDIO_API_BASE` | 是（未设 CDP 覆盖时） | 与 `browser/stop`、`browser/start` 同源 |
| `HUBSTUDIO_CONTAINER` 或 `CONTAINER_CODE` | 是（未设 CDP 覆盖时） | phase-0 环境 ID；缺省时可从 `logs/archive/phase0_env_create_*.jsonl` 最近成功记录解析 |
| `HUBSTUDIO_CDP_URL` | 否 | 若设置：跳过 `browser/stop` / `browser/start`，直接作为 CDP endpoint |
| `OUTLOOK_REGISTER_URL` | 是 | 注册起始页 URL |
| `OUTLOOK_EMAIL_DOMAIN` | 否 | 拼邮箱 `account@域名`，默认 `outlook.com`（勿带 `@` 前缀） |
| `PAGE_LOAD_TIMEOUT_MS` | 否 | `page.goto` 超时（毫秒），默认 100000 |
| `PHASE2_FORM_TIMEOUT_MS` | 否 | 已打开页后单步填表/点击等待（毫秒），默认 15000 |
| `PHASE2_ACTION_DELAY_MS` | 否 | 主步骤间间隔（毫秒），默认 1000；`0` 关闭 |
| `PHASE2_CHROME_PASSWORD_PROMPT` | 否 | `skip` / `save` / `dismiss`；浏览器外壳密码条可能不在 DOM |
| `SCREENSHOTS_DIR` | 否 | 默认 `screenshots` |
| `LOG_DIR` | 否 | 含 `archive/`；phase-2 日志如 `logs/phase2.log` |

### 5.3 可选：Press and hold 人机步骤

| 字段名 | 缺省 | 说明 |
| ------ | ---- | ---- |
| `PHASE2_TRY_HOLD_CHALLENGE` | 关 | `1`/`true`/`yes`/`on` 时尝试无障碍入口 + 长按 |
| `PHASE2_HOLD_AFTER_ACCESSIBLE_MS` | 2500 | 点小人与长按之间间隔 |
| `PHASE2_HOLD_PRESS_DURATION_MS` | 4500 | 长按持续时间（毫秒） |

实现模块：`src/ms_hold_challenge.py` → `try_ms_accessible_hold_challenge`。

### 5.4 phase-2 执行顺序（失败即停）

| 顺序 | 逻辑模块 | 源码 | 说明 |
| ---- | -------- | ---- | ---- |
| 0 | `stop_then_start_browser` | `src/start_hubstudio_browser.py` | 仅当未设 `HUBSTUDIO_CDP_URL`；从 `start` 取 `debuggingPort` |
| 1 | `connect_browser` | `src/connect_browser.py` | `chromium.connect_over_cdp` |
| 2 | `open_signup_page` | `src/open_signup_page.py` | 导航注册 URL |
| 3 | `verify_page` | `src/verify_page.py` | URL 或 DOM 校验 |
| 4 | 读 phase-1 留档 | `src/archive_store.py` | 无记录则 `step=phase2_user_profile` |
| 5 | `apply_outlook_signup_profile` | `src/apply_signup_profile.py` | 填表与提交（约定范围内） |
| 6（可选） | `try_ms_accessible_hold_challenge` | `src/ms_hold_challenge.py` | 由 `PHASE2_TRY_HOLD_CHALLENGE` 控制 |

编排：`src/pipeline.py` → `run_phase2_outlook_signup_page()`；入口：`src/main.py` → `--phase2` / `PHASE=2`。

### 5.5 phase-2 典型 `step` 取值

| `step` | 含义 |
| ------ | ---- |
| `hubstudio_browser_start` | `browser/start` 失败或缺 `debuggingPort` |
| `connect_browser` | CDP 连接失败 |
| `open_signup_page` | 导航失败或超时 |
| `verify_page` | 页面校验未通过 |
| `phase2_user_profile` | 缺少可读 phase-1 成功留档 |
| `apply_signup_profile` | 填表失败；或未启用人机时为最后成功步 |
| `ms_hold_challenge` | 可选人机步失败；或开启且成功后为最后成功步 |

`open_signup_page` / `verify_page` / `apply_signup_profile` 失败时尽量写 `screenshot_path`；`hubstudio_browser_start` / `connect_browser` 失败时通常无 page，多无截图。

---

## 6. 与 narrative 文档的关系

| 主题 | 本文 § | `design.md` 对应（论述与边界） |
| ---- | ------ | ------------------------------ |
| phase-0 字段与命名 | §3 | §3～§8 |
| phase-1 | §4 | §9 |
| phase-2 | §5 | §10 |
| StepResult / archive | §1～§2 | §6、§7.1、§10.8 |

若叙事与表格冲突，**以本文表格与 `src/` 实现为准**，并应回写修正 `design.md`。
