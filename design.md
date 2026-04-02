# 设计说明（Design）

本文档仅覆盖 `requirements.md` 当前确认范围中的 `phase-0`：通过配置文件创建 Hubstudio 指纹浏览器环境。  
`phase-1`、`phase-2` 暂不展开。

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

## 9. 变更记录

| 日期           | 摘要                                                                                                      |
| -------------- | --------------------------------------------------------------------------------------------------------- |
| （用户原始稿） | 见 `design.original.md`                                                                                   |
| 2026-03-20     | 旧版：以 Phase 1（连接与页面验证）为中心                                                                  |
| 2026-03-31     | 重写：仅保留 phase-0，新增可落地字段字典、请求体映射、模块与返回结构                                      |
| 2026-04-01     | 业务向命名与 §8 固化；§8.2：单条/批量统一「网站名+序号+地区+日期」递增                                    |
| 2026-04-01     | 采用 A 方案：系统自动维护序号状态文件（`logs/sequence_state.json`），`name_sequence_start` 仅用于覆盖纠偏 |

