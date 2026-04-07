# 设计说明（Design）

本文档覆盖：

- **phase-0**：Hubstudio 指纹环境创建（§1～§8）。
- **phase-1**：Outlook 注册用用户信息生成（§9）。
- **phase-2**：CDP 连接 + 打开 Outlook 注册页 + 基础 DOM 校验（§10）。

---

## 1. 阶段目标与边界

### 1.1 目标

实现一个可重复执行的 `phase-0` 流程：读取配置 -> 校验必填字段 -> 调用 Hubstudio 创建环境接口 -> 返回统一结构化结果。

### 1.2 成功判据

满足以下条件视为成功：

1. 配置读取成功，必填项校验通过。
2. Hubstudio API 可连通且 `/api/v1/env/create` 返回成功。
3. 返回值中得到可用于后续阶段的环境标识（`containerCode` 或等价字段）。
4. 输出统一结果结构：`success=True`，并记录关键日志。

### 1.3 范围外

- 不启动环境，不打开 Outlook 页面。
- 不执行页面自动化交互。
- 不生成人员身份信息或注册凭据。

---

## 2. 外部依赖与接口约定

### 2.1 外部服务

- Hubstudio 本机 HTTP API（示例：`http://127.0.0.1:6873`）。

### 2.2 目标接口

- 创建环境：`POST /api/v1/env/create`

### 2.3 来源参考（字段提取依据）

字段来自你指定项目 `D:\projects\feitan_statistics\outlook_automation` 的已用实现：

- `src/outlook_automation/hubstudio_adapter.py`
- `run_batch_create.py`
- `ip_pool.json`
- `config.example.ps1`

---

## 3. Hubstudio 环境创建 · 字段字典

本节字段与 **§8 已确认业务规则** 一致；请求体中的固定常量见 §3.2 表下说明。

### 3.1 运行配置（`.env`）

| 字段名               | 类型   | 必填 | 默认值        | 说明                                                 |
| -------------------- | ------ | ---- | ------------- | ---------------------------------------------------- |
| `HUBSTUDIO_API_BASE` | string | 是   | 无            | Hubstudio API 基础地址，例如 `http://127.0.0.1:6873` |
| `LOG_DIR`            | string | 否   | `logs`        | 运行日志目录                                         |
| `SCREENSHOTS_DIR`    | string | 否   | `screenshots` | 失败截图目录（本阶段通常仅异常时可选）               |

### 3.2 输入配置（`hubstudio_env_create_config`）

建议以 **`hubstudio_env_create_config`**（JSON / YAML / 字典）承载以下字段：

| 字段名                   | 类型   | 必填 | 默认值      | 校验规则                                                                               | 映射到 Hubstudio 字段            |
| ------------------------ | ------ | ---- | ----------- | -------------------------------------------------------------------------------------- | -------------------------------- |
| `site_name`              | string | 否   | `outlook`   | 非空；用作环境名中的网站标识（见 §8.2）                                                | 不直接映射                       |
| `region`                 | string | 是   | 无          | 非空；IP/代理所属地区标签（如 `美国`）                                                 | 不直接映射；用于 §8.2 命名与校验 |
| `name_sequence_start`    | int    | 否   | `1`         | **仅首次初始化或人工覆盖时使用**。常规运行由系统按 §8.2 A 方案自动维护“下一可用序号”。 | 不直接映射                       |
| `environment_name`       | string | 否   | 见 §8.2     | 若提供：长度 1–60，且须符合 §8.2；若缺省：按 §8.2 自动生成                             | `containerName`                  |
| `proxy.host`             | string | 是   | 无          | 非空                                                                                   | `proxyServer`                    |
| `proxy.port`             | int    | 是   | 无          | 1–65535                                                                                | `proxyPort`                      |
| `proxy.username`         | string | 是   | 无          | 非空                                                                                   | `proxyAccount`                   |
| `proxy.password`         | string | 是   | 无          | 非空                                                                                   | `proxyPassword`                  |
| `fingerprint.ua`         | string | 否   | 见 §4 示例  | 非空                                                                                   | `advancedBo.ua`                  |
| `fingerprint.ua_version` | string | 否   | `124.0.0.0` | 非空                                                                                   | `advancedBo.uaVersion`           |

**请求体中的固定常量**（与 §8 一致，**不由业务配置覆盖**）：

| 含义     | 值                         | Hubstudio 字段         |
| -------- | -------------------------- | ---------------------- |
| 代理类型 | 仅 **Socks5**              | `proxyTypeName`        |
| 平台     | `windows`                  | `type`                 |
| 浏览器   | `chrome`                   | `browser`              |
| 内核版本 | **124**                    | `coreVersion`          |
| 语言     | **英语** `["en", "en-US"]` | `advancedBo.languages` |
| 动态类型 | `1`（沿用参考实现）        | `asDynamicType`        |

### 3.3 代理字符串兼容输入（可选）

| 字段名      | 类型   | 必填 | 规则                  | 说明                                                        |
| ----------- | ------ | ---- | --------------------- | ----------------------------------------------------------- |
| `proxy_raw` | string | 否   | `host:port:user:pass` | 未提供结构化 `proxy.*` 时拆分为 host/port/username/password |

`proxy_raw` 与 `proxy.*` **二选一**；若同时提供，以 **`proxy.*` 为准**。

---

## 4. 请求体组装规范（调用 Hubstudio）

**Hubstudio 环境创建** 调用 `/api/v1/env/create` 时，统一组装为：

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

说明：

- `asDynamicType=1` 沿用参考实现固定值。
- §8 已锁定的字段（代理类型、语言、内核版本等）**不通过配置覆盖**，避免与 Hubstudio 版本差异混用。
- 上例为 **`name_sequence_start` 默认 1** 时的命名；若 `name_sequence_start=10`，单条则为 `outlook10_美国_2026年4月1日`，批量三条为 `outlook10_…`、`outlook11_…`、`outlook12_…`（见 §8.2）。

---

## 5. 模块设计（Hubstudio 环境创建）

### 5.1 `load_hubstudio_env_config`

职责：

- 从配置文件读取环境创建参数。
- 支持 `proxy_raw` 兼容拆分。

输入：配置文件路径。  
输出：标准化后的 **`hubstudio_env_create_config`** 字典。

### 5.2 `validate_hubstudio_env_config`

职责：

- 校验字段完整性、类型、范围及 §8.2 命名规则。
- 生成可读错误信息，禁止带敏感明文。

输入：`hubstudio_env_create_config`。  
输出：`(is_valid, errors)` 或等价结构。

### 5.3 `create_hubstudio_environment`

职责：

- 根据标准化字段组装请求体并调用 Hubstudio 接口。
- 解析响应并返回环境标识。

输入：已校验配置 + `HUBSTUDIO_API_BASE`。  
输出：统一结果结构（见第 6 节）。

### 5.4 `run_hubstudio_env_creation`

职责：

- 编排 `load_hubstudio_env_config` → `validate_hubstudio_env_config` → `create_hubstudio_environment`。
- 统一日志与异常处理。
- **单条**：环境名中的序号取配置中的 `name_sequence_start`（默认 `1`）。
- **批量**：编排层对第 `k` 条（`k` 从 0 起）使用序号 **`name_sequence_start + k`**，保证同一次运行内连续递增。

输入：配置路径。  
输出：最终 `step=hubstudio_env_creation` 的结构化结果（子步骤可用 `load_config` / `validate_config` / `api_env_create` 等字符串区分）。

---

## 6. 统一返回结构（环境创建）

| 字段              | 类型           | 含义                                              |
| ----------------- | -------------- | ------------------------------------------------- |
| `success`         | bool           | 是否成功                                          |
| `step`            | string         | 主流程为 `hubstudio_env_creation`；可为子步骤名   |
| `message`         | string         | 人类可读结果                                      |
| `data`            | object         | 成功时至少含 `container_code`、`environment_name` |
| `error`           | string \| null | 失败时错误摘要                                    |
| `screenshot_path` | string \| null | 可选；异常时留证路径                              |

成功示例（逻辑）：

```python
{
    "success": True,
    "step": "hubstudio_env_creation",
    "message": "Hubstudio environment created",
    "data": {
        "container_code": 1507473418,
        "environment_name": "outlook1_美国_2026年4月1日"
    },
    "error": None,
    "screenshot_path": None
}
```

失败示例（逻辑）：

```python
{
    "success": False,
    "step": "hubstudio_env_creation",
    "message": "config validation failed",
    "data": {"invalid_fields": ["proxy.port"]},
    "error": "ValidationError",
    "screenshot_path": None
}
```

---

## 7. 日志与可观测性

- 关键日志必须覆盖：配置加载、字段校验、请求发起、响应结果、异常捕获。
- 日志写入 `logs/`；敏感字段（代理账号密码）必须脱敏。
- 失败时必须返回可追溯错误信息，不允许静默失败。

### 7.1 留档（archive）统一规范（phase-0 / phase-1）

为对齐 `requirements.md` 新增需求，统一采用以下 archive 约定：

- **目录**：`logs/archive/`
- **文件命名建议**：
  - phase-0：`phase0_env_create_YYYYMMDD.jsonl`
  - phase-1：`phase1_user_profile_YYYYMMDD.jsonl`
- **记录格式**：一行一个 JSON（JSONL），便于追加写入与后续检索。
- **结果回传**：调用结果中建议包含 `archive_path`（文件路径）或 `archive_ref`（记录ID），至少其一。
- **与日志边界**：
  - `logs/*.log`：运行轨迹（过程日志）
  - `logs/archive/*.jsonl`：业务结果留档（可追溯记录）

---

## 8. 已确认业务规则

以下规则已确认，实现与校验须遵守。

### 8.1 代理类型

- **`proxyTypeName` 仅允许 `Socks5`**，不支持在配置中改为其他代理类型。

### 8.2 环境名称（`containerName` / `environment_name`）

组成要素（顺序固定）：

1. **网站名称**（`site_name`，默认 **`outlook`**）：业务上要注册或使用的站点标识，写入环境名前缀。
2. **序号**（正整数，**单条与批量均使用**）：紧跟在网站名称之后，无下划线分隔（与 `outlook1`、`outlook12` 形式一致），用于在同一 `site_name` + `region` + 日期维度下区分多次创建、多条代理。
3. **IP 地区**（`region`）：与代理/IP 一致的地区标签（如 **`美国`**），**必填**。
4. **本地日期**：创建该环境时 **本机操作系统本地日历** 的日期，格式 **`YYYY年M月D日`**。

**A 方案（已采用）：系统自动维护序号**

- 维护文件：项目根目录 `logs/sequence_state.json`（可改为 `test-results/`，但本版先固定 `logs/`）。
- 状态键建议：`next_sequence_by_site_region_date`（按 `site_name + region + YYYY年M月D日` 维度维护下一可用序号）。
- 运行规则：
  1. 启动创建流程时先读取状态文件；不存在则初始化为 `1`。
  2. 单条创建使用当前 `next_sequence`，成功后自增 `+1` 并落盘。
  3. 批量创建第 `k` 条使用 `next_sequence + k`，整批成功后一次性写回新值。
  4. 若部分失败，仅对“实际创建成功”的条目计入已占用序号，避免跳号失控。
- `name_sequence_start` 作为覆盖参数：仅在初始化历史数据或人工纠偏时使用；覆盖后会同步更新状态文件。

**自动生成规则**（`environment_name` 未在配置中给出时）

统一格式：

`{site_name}{effective_sequence}_{region}_{YYYY年M月D日}`

- **单条**（本次运行只创建 1 个环境）：`effective_sequence = next_sequence`。  
  示例（`start=1`）：`outlook1_美国_2026年4月1日`  
  示例（`start=20`）：`outlook20_美国_2026年4月1日`
- **批量**（同一运行内按列表顺序创建多条）：第 `k` 条（`k` 从 **0** 起）  
  `effective_sequence = next_sequence + k`。  
  示例（`start=5`，三条）：`outlook5_美国_2026年4月1日`、`outlook6_美国_2026年4月1日`、`outlook7_美国_2026年4月1日`

**校验**（`environment_name` 由配置显式给出时）

- 长度 1–60；须与上述格式语义一致：**`site_name` + 数字序号 + `_` + `region` + `_` + 当日 `YYYY年M月D日`**；序号须与当前运行约定下的 `effective_sequence` 一致，否则校验失败。
- 总长度超过 60 时按 Hubstudio 限制截断（实现与参考脚本对齐，截断后仍应尽量保留地区与日期可辨）。

### 8.3 浏览器语言（`advancedBo.languages`）

- **固定为英语**：`["en", "en-US"]`，不提供配置项覆盖。

### 8.4 内核版本（`coreVersion`）

- **固定为 `124`**，不提供配置项覆盖（与参考实现一致）。

---

## 9. phase-1：用户信息生成（Registration identity）

本节对应 `requirements.md` §1.2。不调用 Hubstudio API，不打开浏览器。

### 9.1 目标与边界

- **目标**：生成一条可用于 Outlook 注册流程填写的**合成身份**（非真实证件数据），字段满足格式与复杂度规则。
- **边界**：不发送注册请求、不验证邮箱是否可用、不处理验证码/人机验证。

### 9.2 字段规则（与需求一致）

| 字段 | 规则摘要                                                                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 姓名 | **美国风格**：名 + 姓（可用常见英文名/姓词表或 Faker `en_US` 等实现，具体词表在实现任务中定稿）。                                                                    |
| 生日 | 日期落在 **18～55 周岁（含边界）** 相对「生成当日」或「配置指定参考日」；实现需明确选用其一并在代码注释或配置中写清。                                                |
| 账号 | 由姓名**规范化**（去空格、小写、去特殊字符等，规则在实现中固定）后拼接 **5 位十进制随机数字**；用于注册时的用户名/本地部分，**不等于完整邮箱**除非调用方自行拼域名。 |
| 密码 | **长度 10**；必须同时含 **数字、小写字母、大写字母**（是否允许符号由实现定稿，默认仅三类字符混合即可满足需求）。                                                     |

### 9.3 输出结构

- 复用 `src/step_result.py` 的 **`StepResult`**：`step` 建议取值 `outlook_user_profile`。
- `data` 建议键（可按实现微调，但与 phase-2 对接前需冻结）：`first_name`、`last_name`、`birth_date`（ISO `YYYY-MM-DD`）、`account`、`password`；可选 `display_name`。

### 9.3.2 留档（archive）要求

为对齐 `requirements.md` 新增需求，phase-1 需在“结果输出”之外保留可追溯档案：

- **最小留档字段**：`first_name`、`last_name`、`birth_date`、`account`、`generated_at`、`success`。
- **落盘位置**：遵循 §7.1，建议写入 `logs/archive/phase1_user_profile_YYYYMMDD.jsonl`。
- **可追溯标识**：调用结果建议返回 `archive_path` 或 `archive_ref`（至少其一），便于后续 phase-2 对接。
- **与日志边界**：`logs/*` 是运行日志；archive 是业务结果留存，两者不可混用。

### 9.3.1 冻结接口（本仓库当前实现）

为避免 phase-2 对接时字段漂移，现将 phase-1 产物接口冻结如下：

- **StepResult.step**：`outlook_user_profile`
- **StepResult.data keys（固定）**：`first_name`、`last_name`、`birth_date`、`account`、`password`

### 9.4 模块与入口（建议）

| 项       | 建议                                                                                                                              |
| -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 核心模块 | 新建 `src/outlook_user_profile.py`（或等价命名），对外暴露 `generate_outlook_user_profile(...)`。                                 |
| 随机源   | 优先 `secrets`；单测可用 **可注入 seed**（**随机种子**：固定种子使「随机」输出可重复，便于测试）。                                |
| 编排     | 可在 `src/pipeline.py` 增加 `run_phase1_user_profile()`，或由 `main.py` 用子命令/`PHASE` 环境变量切换；具体在 **T-P1-003** 定稿。 |
| 日志     | 成功/失败写入现有日志体系；**禁止**在日志中打印完整密码（可打掩码或省略）。                                                       |

### 9.5 与 phase-0 / phase-2 的关系

- **phase-0**：独立；phase-1 不依赖 `containerCode`，但可引用 phase-0 的 archive 信息做运行关联。
- **phase-2**：消费 phase-1 的 `data` + phase-0 的环境标识（启动浏览器后再填表）。

---

## 10. phase-2：Outlook 注册页基础流程（CDP + Playwright）

本节对应 `requirements.md` §1.3，并与 `test.md` 中 **TC-P2-001～TC-P2-005** 对齐。

### 10.1 目标与边界

- **目标**：按 `requirements.md` §1.3，以 **phase-0 产出的环境 ID**（`containerCode`）经 Hubstudio **打开环境**（默认路径见下节「边界」），取得 **`debuggingPort` 对应的 HTTP 调试端点**（或 `HUBSTUDIO_CDP_URL` 覆盖）后，用 Playwright **`connect_over_cdp`** 附着**已运行**的指纹浏览器，打开可配置的 Outlook 注册 URL；在**超时控制**下完成导航与**加载/状态判断**，并做**基础 URL 或 DOM 校验**（与 `verify_page` 策略一致）。全程返回统一 `StepResult`。
- **自动化约束（对齐工程 `.cursorrules` §六）**：**不**将页面结构或某一元素存在性当作不变前提；优先保证**日志、失败截图、超时与状态判断**可追溯。出现异常时按 **代码层 / 页面层（DOM、加载、跳转）/ 环境层（Hubstudio、CDP 端口）/ 网络层（代理、连接、超时）** 分层分析；**禁止**在缺少 `requirements.md` / `test.md` 依据时做推测性 DOM 或流程实现。
- **边界（当前实现）**：
  - 默认路径：先 **best-effort** `POST /api/v1/browser/stop`，再 `POST /api/v1/browser/start`（[官方说明](https://support-orig.hubstudio.cn/0379/7beb/fbb0/6964)），用返回的 **`debuggingPort`** 拼出 `http://127.0.0.1:{port}` 供 `connect_over_cdp`。原因：成功 `start` 的 JSON 无可靠「已在运行」标志；环境已开时常报业务码（如 **-10013**），且需**新的**调试端口时以 stop→start 统一策略。
  - **调试/兼容**：若已手动启动环境并已知 CDP，可设置 **`HUBSTUDIO_CDP_URL`**，编排层**跳过** `browser/stop` 与 `browser/start`，直接连接。
  - **不**在本节要求内实现完整注册提交、验证码/人机绕过、多步表单填完。

### 10.2 CDP 与 HTTP API 区分（易混点）

| 能力           | 典型配置 / 协议                                                                                      | 用途                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Hubstudio HTTP | `HUBSTUDIO_API_BASE`（如 `http://127.0.0.1:6873`）                                                   | phase-0 `env/create`；**phase-2 默认** `browser/stop`（best-effort）+ `browser/start` |
| 浏览器 CDP     | 由 `debuggingPort` 推导的 `http://127.0.0.1:port`，或手填 `HUBSTUDIO_CDP_URL`（`ws://` / `http://`） | Playwright `connect_over_cdp`                                                         |

phase-2 配置由 **`load_phase2_settings()`**（`src/config.py`）加载，**不再**使用仅含 CDP 的 `load_settings()` 作为主路径。

### 10.3 运行配置（`.env`，经 `load_phase2_settings`）

| 字段名                                    | 默认路径下必填        | 说明                                                                                                                                      |
| ----------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `HUBSTUDIO_API_BASE`                      | 是（未设 CDP 覆盖时） | 与 `browser/stop`、`browser/start` 同源，如 `http://127.0.0.1:6873`。                                                                     |
| `HUBSTUDIO_CONTAINER` 或 `CONTAINER_CODE` | 是（未设 CDP 覆盖时） | phase-0 环境 ID；若缺省则尝试从 `logs/archive/phase0_env_create_*.jsonl` 最近一条 `success` 记录解析 `containerCode` / `container_code`。 |
| `HUBSTUDIO_CDP_URL`                       | 否                    | 若设置：跳过 `browser/stop` / `browser/start`，直接作为 `connect_over_cdp` 的 endpoint（联调旧流程）。                                    |
| `OUTLOOK_REGISTER_URL`                    | 是                    | 注册流程起始页。                                                                                                                          |
| `OUTLOOK_EMAIL_DOMAIN`                    | 否                    | 拼接邮箱 `account@域名`，缺省 `outlook.com`（勿带 `@` 前缀）。                                                                              |
| `PAGE_LOAD_TIMEOUT_MS`                    | 否                    | 控制 `page.goto`（页面跳转）操作的最大超时时间（毫秒）。`page.goto` 是 Playwright 的页面主导航方法，用于跳转并等待页面内容加载。默认 100000。 |
| `PHASE2_FORM_TIMEOUT_MS`                  | 否                    | **已打开页后**单步填表/点击等待（毫秒），缺省 15000；与 `PAGE_LOAD_TIMEOUT_MS` 解耦，避免填邮箱前空等过久。                                  |
| `PHASE2_ACTION_DELAY_MS`                 | 否                    | 各**主步骤**之间的额外间隔（毫秒），缺省 1000；设为 `0` 可关闭。                                                                           |
| `PHASE2_CHROME_PASSWORD_PROMPT`          | 否                    | 密码步提交后是否尝试处理 Chrome 系密码条：缺省 `skip`（不尝试）；显式设为 `save` 时尽量点「更新密码/保存」，`dismiss` 尽量点「不用了」。**提示条常在浏览器外壳，可能不在页面 DOM，不保证命中**。 |
| `SCREENSHOTS_DIR`                         | 否                    | 失败截图目录，缺省 `screenshots`。                                                                                                        |
| `LOG_DIR`                                 | 否                    | 含 `archive/`；phase-2 运行日志 `logs/phase2.log`。                                                                                       |

### 10.4 执行顺序与模块映射

固定顺序（任一步失败即停止，返回该步 `StepResult`）：

0. **`stop_then_start_browser`**（`src/start_hubstudio_browser.py`）— 仅当**未**设置 `HUBSTUDIO_CDP_URL`
   - `POST …/browser/stop`（best-effort，失败或非 0 业务码不阻断）→ `POST …/browser/start`，body 均含 `containerCode`
   - 从 `start` 响应 `data.debuggingPort` 得到 CDP 入口：`http://127.0.0.1:{debuggingPort}`
   - **仅**当最终 `start` 失败或缺端口时 `step=hubstudio_browser_start`
1. **`connect_browser`**（`src/connect_browser.py`）
   - `chromium.connect_over_cdp(cdp_url)`（`cdp_url` 来自上一步或 `HUBSTUDIO_CDP_URL`）
2. **`open_signup_page`**（`src/open_signup_page.py`）
3. **`verify_page`**（`src/verify_page.py`）  
   - **URL** / **DOM** 策略同前；`url_ok` **或** `element_ok` 为真即 `success=True`。
4. **读取 phase-1 留档**（`archive_store.read_latest_phase1_user_profile`）  
   - 无最近成功记录时 `step=phase2_user_profile`，`error=Phase1ArchiveMissing`。
5. **`apply_outlook_signup_profile`**（`src/apply_signup_profile.py`）  
   - 邮箱 → 下一步 → 密码 → 下一步 →（可选，由 `PHASE2_CHROME_PASSWORD_PROMPT` 控制）**密码提示**：DOM 点击失败且 `save` 时再 **Enter**（猜测焦点在主按钮）→ **先生日**、再姓名；若当前屏无姓名则 **Next** 后再填姓名；最后 **Next**；`birth_date` 为 `YYYY-MM-DD`；单步超时由 `PHASE2_FORM_TIMEOUT_MS`；主步骤间可插入 `PHASE2_ACTION_DELAY_MS`。  
   - **生日**：填前 **Escape** 收起国家/地区浮层；现版 live 为 **Fluent**（英文无障碍名如 Birth month/day、Birth year，选项为 January / 数字日等）。listbox 通过 **aria-controls → fluent-listbox** 在 Page 上定位。`get_by_test_id("primaryButton")` 作提交按钮候选之一。  
   - `verify_page` 内候选元素等待**单独缩短**（与 `PAGE_LOAD_TIMEOUT_MS` 成比例上限约 6s），减少首屏校验耗时。  
   - 全流程成功时写入 **phase-2 留档**（§10.8），最终 `step=apply_signup_profile`，`data` 含 `steps_completed`、`email_used`、`archive_path` / `archive_ref`（不含密码）。

**编排入口**：`src/pipeline.py` → `run_phase2_outlook_signup_page()`。
**程序入口**：`src/main.py` → `--phase2` / `PHASE=2`。

### 10.5 统一返回与 `step` 取值

| `step`（典型）            | 含义                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------ |
| `hubstudio_browser_start` | `browser/stop`→`browser/start` 流程中最终 `start` 失败（HTTP/业务码/缺 `debuggingPort`）。 |
| `connect_browser`         | CDP 连接失败。                                                                             |
| `open_signup_page`        | 导航失败或超时。                                                                           |
| `verify_page`             | 页面校验未通过。                                                                           |
| `phase2_user_profile`     | 缺少可读 phase-1 成功留档。                                                                |
| `apply_signup_profile`    | 录入失败或**全流程成功时的最终一步**（`success=True`）。                                   |

失败时：`error` 为非空字符串；`open_signup_page` / `verify_page` / `apply_signup_profile` 在可能时写入 `screenshot_path`（`screenshots/` 下 PNG）。**注意**：`hubstudio_browser_start` / `connect_browser` 失败时通常**无**可用 `page`，一般不截图，以日志与 `error` 为准。

### 10.6 可观测性与排障

- **日志**：`logs/phase2.log`（关键步骤、流水线结果、错误栈摘要由 Playwright 抛出）。
- **截图**：`screenshots/open_signup_page.png`、`screenshots/verify_page.png`、`screenshots/apply_signup_profile.png`（按失败点覆盖写入）。
- **已知环境问题**：若出现 `ECONNREFUSED` 指向 CDP 端口，表示该端口未监听或 URL 错误；见 `debug_log.md` 中 phase-2 CDP 条目。

### 10.7 与 `test.md` 用例对应（验收口径）

| `test.md` 用例 | 设计要点                                                                                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TC-P2-001      | 未设 `HUBSTUDIO_CDP_URL` 时：先 best-effort `browser/stop` 再 `browser/start` 成功；随后 `connect_browser` 且 `success=True`。仅 CDP 模式：直接 `connect_browser` 成功。 |
| TC-P2-002      | `step=open_signup_page` 且 `data.current_url` 有值。                                                                                                                     |
| TC-P2-003      | `verify_page` 成功（中间步，最终 `step` 可能为 `apply_signup_profile`）。                                                                                                |
| TC-P2-004      | 单次 `--phase2` 跑通全流程：须先有 phase-1 留档；最终 `step=apply_signup_profile` 且 `success=True`，`data` 含留档字段。                                                     |
| TC-P2-005      | 故意错误环境 ID、CDP 或 URL 时 `success=False`；open/verify 失败时尽量带 `screenshot_path`。                                                                             |

### 10.8 phase-2 留档与后续扩展

- **已实现**：`apply_outlook_signup_profile` 成功后追加 `logs/archive/phase2_signup_smoke_YYYYMMDD.jsonl`（`append_archive_record`，`phase=phase2_signup_smoke`）；`StepResult.data` 增加 `archive_path`、`archive_ref`。载荷含 `container_code`（若有）、`used_cdp_url_override`、`current_url`、`url_ok` / `element_ok` / `element_hit`、`steps_completed`、`email_used`、`verified_at`，**不含密码**。
- 选择器随微软页面改版迭代时，应**单次最小变更** `verify_page.py` / `apply_signup_profile.py`，并更新本节说明。

---

## 11. 变更记录

| 日期           | 摘要                                                                                                       |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| （用户原始稿） | 见 `design.original.md`                                                                                    |
| 2026-03-20     | 旧版：以 Phase 1（连接与页面验证）为中心                                                                   |
| 2026-03-31     | 重写：仅保留 phase-0，新增可落地字段字典、请求体映射、模块与返回结构                                       |
| 2026-04-01     | 业务向命名与 §8 固化；§8.2：单条/批量统一「网站名+序号+地区+日期」递增                                     |
| 2026-04-01     | 采用 A 方案：系统自动维护序号状态文件（`logs/sequence_state.json`），`name_sequence_start` 仅用于覆盖纠偏  |
| 2026-04-02     | 新增 §9：phase-1 用户信息生成设计                                                                          |
| 2026-04-02     | 新增 §10：phase-2 CDP + 注册页设计；变更记录顺延为 §11                                                     |
| 2026-04-02     | §10 修订：phase-2 默认 `browser/start` + `debuggingPort` 连 CDP；`load_phase2_settings`；留档解析环境 ID   |
| 2026-04-03     | §10：phase-2 默认路径改为 best-effort `browser/stop` 后 `browser/start`，避免已开环境 -10013 与旧 CDP 端口 |
| 2026-04-03     | §10.1：目标与自动化约束对齐 `.cursorrules` §六（可观测性、不假设 DOM、问题分层）                              |
| 2026-04-03     | §10.8：phase-2 成功留档 `phase2_signup_smoke`；任务表 T-P2-006                                                     |
| 2026-04-03     | §10：phase-2 增加 phase-1 留档读取与 `apply_signup_profile`；最终成功 `step=apply_signup_profile`                  |
| 2026-04-03     | §10：`PHASE2_FORM_TIMEOUT_MS`；`apply_signup_profile` 扩展人物身份与中间提交；`verify_page` 缩短元素等待            |
| 2026-04-06     | §10.3：缺省超时略增；新增 `PHASE2_ACTION_DELAY_MS`、`PHASE2_CHROME_PASSWORD_PROMPT`；§10.4 编排说明同步                     |
| 2026-04-06     | §10.4：`apply_signup_profile` 密码提示 Enter 回退；人物信息顺序改为先生日再姓名，支持姓名在下一屏                                |
