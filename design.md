# 设计说明（Design）

本文档阐述各阶段的**目标、边界、模块如何协作**，以及 phase-2 **页面自动化实现要点**（为何默认 stop→start、DOM 策略摘要等）。

凡「`.env` 键、Hubstudio 字段映射、请求体示例、冻结 `data` 键、留档文件名、`step` 枚举、流水线顺序」等**表格级契约**，均以 [`docs/contracts.md`](docs/contracts.md) 为唯一权威（修改配置或对接产物时先改该文件与代码，再同步本说明中的叙述）。术语见 [`docs/glossary.md`](docs/glossary.md)，需求验收见 [`requirements.md`](requirements.md)，追溯矩阵见 [`docs/codemap.md`](docs/codemap.md)。

---

## 1. phase-0：Hubstudio 指纹环境创建 · 目标与边界

### 1.1 目标

实现可重复流程：读取配置 → 校验必填 → 调用 `POST /api/v1/env/create` → 返回统一 `StepResult`（含环境标识，供 phase-2 启动浏览器）。

### 1.2 成功判据

1. 配置读取成功，必填项校验通过。
2. Hubstudio API 可连通且创建接口返回成功。  
3. 得到可用于后续阶段的环境标识（`containerCode` 或等价字段）。  
4. `success=True`，关键步骤有日志。

### 1.3 范围外

不启动浏览器环境、不连接 CDP、不打开 Outlook、不做页面自动化、不生成注册用合成身份（由 phase-1 负责）。

---

## 2. 外部依赖与参考实现

- **Hubstudio 本机 HTTP API**（示例：`http://127.0.0.1:6873`）。  
- **创建接口**：`POST /api/v1/env/create`。  
- 字段与请求体形态曾对齐参考仓库 `D:\projects\feitan_statistics\outlook_automation` 中 `hubstudio_adapter.py`、`run_batch_create.py`、`ip_pool.json`、`config.example.ps1` 等；**以实现与 `docs/contracts.md` 为准**。

---

## 3. phase-0：模块职责与编排

| 环节（概念） | 职责摘要 |
| ------------ | -------- |
| 配置加载 | 读取 `.env` 与 `hubstudio_env_create_config`，支持 `proxy_raw` 拆分 → `src/config.py` |
| 校验 | 完整性、类型、范围及命名规则（与 `docs/contracts.md` §3.6 一致）→ `src/validate_hubstudio_env_config.py` |
| 创建 API | 组装请求体并调用 `env/create` → `src/create_hubstudio_environment.py` |
| 编排 | `load` → `validate` → `create`，序号提交与 archive → `src/pipeline.py` |

**字段表、请求体 JSON 示例、主 `step`、留档路径**见 `docs/contracts.md` §3、§3.7 与 §2。

---

## 4. phase-0：可观测性与安全

- 日志须覆盖：配置加载、校验、请求与响应、异常；代理凭据等敏感信息须脱敏。  
- 失败须返回可读错误，禁止静默失败。  
- **留档与运行日志的边界、`archive_path` / `archive_ref`**见 `docs/contracts.md` §2。

---

## 5. phase-1：Outlook 注册用用户信息生成

对应 `requirements.md` §1.2。

- **目标**：生成一条可用于填表的**合成身份**；不调用 Hubstudio、不打开浏览器、不提交注册。  
- **字段规则、冻结 `StepResult.step` / `data` 键、留档约定、运行入口**见 `docs/contracts.md` §4。  
- **源码与任务/用例映射**见 `docs/codemap.md`。  
- **关系**：与 phase-0 独立；phase-2 消费本阶段留档与 phase-0 环境 ID。

---

## 6. phase-2：CDP 附着与 Outlook 注册页自动化

对应 `requirements.md` §1.3。**验收用例**见 `test.md` §4 与 `docs/codemap.md`。

### 6.1 目标与边界

- 使用 phase-0 的**环境 ID**，经 Hubstudio **启停浏览器**（或 `HUBSTUDIO_CDP_URL` 直连）获得 CDP 端点，用 Playwright **`connect_over_cdp`** 附着**已在运行**的指纹浏览器，打开可配置注册 URL，在超时控制下完成导航与加载判断，并按 phase-1 留档在**约定范围**内填表与中间提交。  
- **自动化约束**（对齐 `.cursorrules`）：不将 DOM 结构视为永久不变；优先日志、截图、超时与明确 `step`。排障时区分**代码层 / 页面层 / 环境层（Hubstudio、CDP）/ 网络层**。  
- **默认启停策略**：best-effort `POST /api/v1/browser/stop` 再 `POST /api/v1/browser/start`（[Hubstudio 说明](https://support-orig.hubstudio.cn/0379/7beb/fbb0/6964)），用 `debuggingPort` 拼 `http://127.0.0.1:{port}` 连接 CDP；用于规避「已开环境」业务码（如 **-10013**）与旧调试端口。若已手动启动且已知 CDP，可设 **`HUBSTUDIO_CDP_URL`** 跳过 HTTP 启停。  
- **范围外**：不保证验证码、人机、短信/邮箱验证、风控后续页闭环（见 `requirements.md` §4）。

### 6.2 配置、执行顺序与 `step`

**环境变量表、Hubstudio HTTP 与 CDP 的区分、流水线顺序、`step` 含义、可选长按人机变量**见 `docs/contracts.md` §5。

### 6.3 实现要点（页面与脚本行为）

- **`apply_signup_profile`**（行为摘要，非选择器契约）：邮箱 → 下一步 → 密码 → 下一步；`PHASE2_CHROME_PASSWORD_PROMPT` 控制是否处理 Chrome 系密码条——条常在外壳层，**DOM 可能不可达**；`save` 模式下点击失败时可回退 `Enter`。人物信息：**先**生日 **后**姓名；若当前屏无姓名则 **Next** 后再填；填生日前 **`Escape`** 收起国家/地区浮层。当前页面对齐 **Fluent** 时，可用英文无障碍名（Birth month/day、Birth year 等）与 **`aria-controls` → `fluent-listbox`**；`get_by_test_id("primaryButton")` 为提交按钮候选。单步等待由 `PHASE2_FORM_TIMEOUT_MS`；主步骤间可插入 `PHASE2_ACTION_DELAY_MS`。**行为模拟（P0+P1）**：`PHASE2_BEHAVIOR_SIMULATION` 为 `light` / `medium` 时，在每个主步骤 pause 之后**再**叠加 `[min,max]` 毫秒内均匀随机延迟（默认区间见 `docs/contracts.md` §5.2）；可与 `PHASE2_ACTION_DELAY_MS` **叠用**。流水线在填表前打 **`phase2 behavior_profile`**；成功 `data` 含 **`behavior_profile`**。  
- **`verify_page`**：候选元素等待上限与 `PAGE_LOAD_TIMEOUT_MS` 成比例（约 6s 量级），减轻首屏校验耗时。  
- **phase-2 成功留档**：见 `docs/contracts.md` §2.3；在 `apply_signup_profile` 及可选 `ms_hold_challenge` 成功后追加 JSONL。  
- **选择器维护**：微软改版时**最小差异**修改 `verify_page.py` / `apply_signup_profile.py` / `ms_hold_challenge.py`，并同步更新本段或契约叙述。

### 6.4 可观测性与排障

- 日志：`logs/phase2.log`。  
- 截图：`screenshots/`（如 `open_signup_page.png`、`verify_page.png`、`apply_signup_profile.png` 等）。  
- **`ECONNREFUSED` 指向本地 CDP 端口**：多为端口未监听或 URL 错误，见 `debug_log.md`。

### 6.5 「Press and hold」人机步骤（接在填表之后）

主流程在 **`apply_outlook_signup_profile` 成功之后** 调用 `try_ms_accessible_hold_challenge`（与 `src/pipeline.py` 顺序一致）。**未设置** `PHASE2_TRY_HOLD_CHALLENGE` 时**默认尝试**人机；显式 `0` / `false` / `no` / `off` 可关闭。人机检测前默认**短睡 4s + 最多轮询 20s**（`PHASE2_HOLD_PREP_*`，见 `docs/contracts.md` §5.3），减轻「填表刚结束人机卡片尚未渲染」导致的误跳过；跳过且原因为未识别时写入带时间戳的 `screenshots/ms_hold_challenge_skipped_*.png`。流水线成功结束时 **`step` 为人机步骤名**（含跳过情形），便于与日志对照。

**挑战根节点选择（路线 A，V1）**：在 **iframe.hsprotect.net** 等 URL 的 frame 与「含人机正文」的 frame 中优先（子 frame 逆序）；主文档常残留说明文案故**排在后**；若已锁定 `iframe` / `iframe_hsprotect`，长按前 **refind 不会降回 main**（避免误把操作范围切回顶层）。**Press and hold** 除 `<button>` 外兼容 **`<p>` 文案** 与 `Press & hold` 变体；无障碍入口兼容 **`a[role="button"]`**。prep 轮询用「任一处出现人机文案或 hsprotect frame」判定。日志关键行带 **`[MS_HOLD] stage=…`** 前缀。失败时 `data` 含 **`hsprotect_url_bases`**（去 query 摘要）便于对照。外壳层「保存密码」仍可能不在 DOM：建议在 `.env` 设 **`PHASE2_CHROME_PASSWORD_PROMPT=dismiss`** 并配合 HubStudio 关闭提示。

**视口热身点击**：在关完 DOM 可达的密码条之后、点小人文之前，默认在**顶层 Page 视口**做一次 `mouse.click`（坐标偏左下，减轻误点右上密码条），由 **`PHASE2_HOLD_WARMUP_VIEWPORT_CLICK`** / **`PHASE2_HOLD_WARMUP_SETTLE_MS`** 控制（见 `docs/contracts.md` §5.3）。

**Locator 顺序与探测超时（A+B）**：无障碍优先 **`a`/`button` 精确匹配 `Accessible challenge`**；长按优先 **`Press & Hold Human Challenge` / `Press and hold` 的 role+name 与 aria-label`**。各候选 **`wait_for(visible)`** 上限由 **`PHASE2_HOLD_LOCATOR_PROBE_MS`** 控制，点击超时仍为 **`PHASE2_FORM_TIMEOUT_MS`**。返回与日志中带 **`timing_ms`** / `[MS_HOLD] stage=timing`。

### 6.6 浏览器会话与「关浏览器」的影响（项目结论，单点说明）

以下结论来自实际验证，**其它文档不重复展开**，仅作交叉引用。

1. **关浏览器或 Hubstudio `browser/stop`→`start` 会结束当前浏览器进程**。在本场景中，注册流程依赖的**页面会话/进度往往会丢失**，表现为需**重新打开注册页并重新填写**，**不能**指望「先关掉浏览器拿新调试地址，再在同一流程里接着做人机」。
2. **主流程顺序**：在同一次 CDP 附着会话内完成「打开注册页 → 校验 → 填表 → **人机尝试**」。人机必须在**未主动关掉该会话**的前提下接在填表之后执行（见 `src/pipeline.py`）。
3. **若必须保留已填好的页面、仅让脚本附着操作**：应使用 **`HUBSTUDIO_CDP_URL`** 直连**当前仍在运行**的浏览器调试地址，**避免**仅用环境 ID 触发会执行 stop/start 的路径（见 §6.1）。
4. **`tools/hubstudio_cdp_probe`** 会反复 stop/start，**只适用于观测调试端口变化**，**不要**在需要保留注册进度时对同一环境运行。

---

## 7. 变更记录

| 日期 | 摘要 |
| ---- | ---- |
| 2026-04-09 | §6.3：行为模拟 P0+P1（`PHASE2_BEHAVIOR_*`、留档 `behavior_profile`） |
| 2026-04-09 | §6.5：locator 顺序+A+B+D（`PHASE2_HOLD_LOCATOR_PROBE_MS`、`timing_ms`）；视口热身；路线 A；密码条建议 dismiss |
| 2026-04-08 | §6.5～§6.6：填表后人机默认启用；关浏览器与会话丢失结论（单点说明）；与 pipeline 顺序对齐 |
| 2026-04-08 | **文档收束（第二部分）**：表格与枚举迁至 `docs/contracts.md`；`design.md` 重排为 §1～§7，仅保留目标、边界、模块协作与 phase-2 实现要点 |
| 2026-04-07 | §10.9：可选 `ms_hold_challenge`；`PHASE2_TRY_HOLD_CHALLENGE` 等（历史：旧 §10） |
| 2026-04-06 | `PHASE2_ACTION_DELAY_MS`、`PHASE2_CHROME_PASSWORD_PROMPT`；人物信息顺序先生日后姓名（历史：旧 §10） |
| 2026-04-03 | phase-2 默认 `browser/stop` 后 `browser/start`；phase-1 留档与 `apply_signup_profile`；`PHASE2_FORM_TIMEOUT_MS`（历史：旧 §10） |
| 2026-04-02 | phase-2：`browser/start` + `debuggingPort`；`load_phase2_settings`；留档解析环境 ID（历史：旧 §10） |
| 2026-04-02 | 新增 phase-1 设计（历史：旧 §9） |
| 2026-04-01 | A 方案序号状态文件；业务命名 §8.2（历史：内容已迁入 `contracts` §3.6） |
| 2026-03-31 | phase-0 字段字典与请求体（历史：已迁至 `contracts` §3） |
| 2026-03-20 | 旧版以「Phase 1（连接与页面验证）」为中心 |
| （用户原始稿） | 见 `design.original.md` |
