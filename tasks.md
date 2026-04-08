# 任务列表（Tasks）

> 按优先级执行；完成一项再开下一项。状态：`待办` / `进行中` / `已完成` / `阻塞`。  
> **当前目标**：**phase-2**（`requirements.md` §1.3）— 连接 Hubstudio（CDP）并打开 Outlook 注册页完成基础 DOM 校验；phase-1 已完成。  
> **需求章节 ↔ 源码 ↔ 本表任务 ↔ 测试用例**的矩阵见 `docs/codemap.md`。

## 〇、阶段对照（避免混淆）

| `requirements.md` | 含义                                                     |
| ----------------- | -------------------------------------------------------- |
| phase-0           | Hubstudio 环境创建（本仓库已实现主路径）                 |
| **phase-1**       | **用户信息生成（已完成，接口冻结）**                     |
| phase-2           | 启动环境、打开 Outlook 注册页、基础 DOM 校验（当前迭代） |

说明：旧版任务里曾用「Phase 1」指**页面自动化**，与需求文档编号不一致；**以 `requirements.md` 的 phase-0/1/2 为准**。

---

## 一、phase-0 基线（已完成，维护即可）

已交付能力闭环：

1. 读取环境创建配置（`.env` + `hubstudio_env_create_config`）
2. 校验字段与命名规则
3. 调用 `POST /api/v1/env/create`
4. 统一 `StepResult` 与日志

仍可选：**T-003-4** 批量多环境创建（见 §三）。

phase-0 期间明确不做的事项（phase-1 仍不做）：不连 CDP、不打开 Outlook 页面。

---

## 二、模块与文件映射

### phase-0（已实现）

| 顺序 | 模块       | 源码文件                               | 说明                                   |
| ---- | ---------- | -------------------------------------- | -------------------------------------- |
| 1    | 配置读取   | `src/config.py`                        | `.env` + 创建配置                      |
| 2    | 字段校验   | `src/validate_hubstudio_env_config.py` | 命名与必填                             |
| 3    | 序号与名称 | `src/sequence_state.py` + pipeline     | A 方案序号（非 `environment_name.py`） |
| 4    | API 调用   | `src/create_hubstudio_environment.py`  | `env/create`                           |
| 5    | 编排       | `src/pipeline.py`                      | `run_hubstudio_env_creation`           |
| 6    | 入口       | `src/main.py`                          | phase-0 主入口                         |

### phase-1（已实现，接口冻结）

| 顺序 | 模块         | 建议源码文件                  | 目的                              |
| ---- | ------------ | ----------------------------- | --------------------------------- |
| 1    | 身份生成     | `src/outlook_user_profile.py` | 姓名/生日/账号/密码生成与规则校验 |
| 2    | 编排（可选） | `src/pipeline.py`             | `run_phase1_user_profile` 或等价  |
| 3    | 入口扩展     | `src/main.py`                 | 子命令或环境变量选择 phase        |

---

## 三、当前迭代任务（phase-0 维护 + phase-1 开发）

### 3.1 phase-0 任务（归档 / 维护）

| ID    | 任务                                                             | 状态             | 验收标准                                                                                              |
| ----- | ---------------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------- |
| T-001 | 对齐文档基线：`requirements.md` + `design.md` + 本任务清单一致   | 已完成           | 当时以 phase-0 为迭代目标；现 design 含 phase-1 叙事（§5），契约见 `docs/contracts.md`                    |
| T-002 | 实现配置模型与读取逻辑（`.env` + `hubstudio_env_create_config`） | 已完成           | `src/config.py`：`load_hubstudio_env_create_config`                                                   |
| T-003 | 实现命名规则与序号策略（A 方案）                                 | 已完成（单条）   | `src/sequence_state.py` + `pipeline` 接入；**批量 T-003-4 仍待办**                                    |
| T-004 | 实现字段校验逻辑                                                 | 已完成           | `src/validate_hubstudio_env_config.py`                                                                |
| T-005 | 实现 Hubstudio 创建接口调用                                      | 已完成           | `src/create_hubstudio_environment.py`                                                                 |
| T-006 | 实现编排与统一返回结构                                           | 已完成（主路径） | `src/pipeline.py` + `step_result`；可再收紧文案与边界                                                 |
| T-007 | 增加最小可用验证（手工或脚本）                                   | 部分完成         | `scripts/test_env_create_api.py`；系统化 pytest 非 phase-1 阻塞项                                     |
| T-008 | 更新测试文档与排障记录（仅 phase-0）                             | 已完成           | `test.md`、`debug_log.md` 已对齐 phase-0                                                              |
| T-009 | phase-0 创建结果留档（archive）规范化                            | 已实现（待验收） | 已接入 `pipeline.py` 写入 archive 并回传 `archive_path/archive_ref`；待在可成功创建环境的机器完成验收 |

### 3.2 phase-1 任务（按推荐顺序）

| ID       | 任务                                                                        | 状态   | 验收标准                                                                                                                                     |
| -------- | --------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| T-P1-001 | 定义数据模型与生成函数签名（`StepResult`、`data` 键）                       | 已完成 | `src/outlook_user_profile.py` + `run_phase1_user_profile` 输出结构化 `StepResult`                                                            |
| T-P1-002 | 实现姓名、生日（18–55）、账号（规范名 + 5 位随机数）、密码（10 位三类字符） | 已完成 | 随机生成 + 内部校验（单测覆盖生日区间/密码字符类/账号后缀）                                                                                  |
| T-P1-003 | 接入 `pipeline` / `main`（与 phase-0 并列或分模式运行）                     | 已完成 | `src/main.py --phase1` + `src/pipeline.py` 提供 phase-1 入口（日志脱敏密码）                                                                 |
| T-P1-004 | 更新 `test.md`：增加 phase-1 用例与通过门槛                                 | 已完成 | 已补充 TC-P1-001～003（phase-1）                                                                                                             |
| T-P1-005 | `.env.example` 补充 phase-1 可选配置（若有，如 `USER_GEN_SEED`）            | 已完成 | 已补充 `PHASE=1` / `USER_GEN_SEED`（无敏感默认值）                                                                                           |
| T-P1-006 | phase-1 用户信息留档（archive）规范化                                       | 已完成 | 已落盘 `logs/archive/phase1_user_profile_YYYYMMDD.jsonl`；回传 `archive_path/archive_ref`；archive 当前允许保存明文 `password`（日志仍脱敏） |

#### phase-1 冻结接口（对接 phase-2 前不得随意改）

- **运行入口**：`python src/main.py --phase1`（或 `PHASE=1`）
- **StepResult.step**：固定为 `outlook_user_profile`
- **StepResult.data keys**（固定）：`first_name`、`last_name`、`birth_date`（ISO `YYYY-MM-DD`）、`account`、`password`
- **日志脱敏**：日志中 `password` 必须输出为 `***`（不允许明文）

### 3.3 phase-2 任务（按推荐顺序）

| ID       | 任务                                          | 状态   | 验收标准                                                                                      |
| -------- | --------------------------------------------- | ------ | --------------------------------------------------------------------------------------------- |
| T-P2-001 | best-effort `browser/stop` + `browser/start`（环境 ID）+ `connect_browser`（`debuggingPort` 或 `HUBSTUDIO_CDP_URL`） | 已完成 | 默认路径：`hubstudio_browser_start`（最终 start 成功）且 `connect_browser` 成功；或仅 CDP 覆盖时直连成功 |
| T-P2-002 | 实现 `open_signup_page`：导航到注册 URL       | 已完成 | 连接成功后 `step=open_signup_page` 返回 `success=True`；失败有 `screenshot_path`              |
| T-P2-003 | 实现 `verify_page`：URL 或注册元素校验        | 已完成 | `step=verify_page` 返回 `success=True`；失败有截图便于微调选择器                              |
| T-P2-004 | `main/pipeline` 增加 phase-2 入口与阶段日志   | 已完成 | `python src/main.py --phase2` 正常执行并输出结构化结果；phase2 日志落在 `logs/phase2.log`     |
| T-P2-006 | `apply_signup_profile` 成功后写入 `logs/archive/phase2_signup_smoke_*.jsonl` | 已完成 | 返回 `data.archive_path` / `archive_ref`；字段含 `container_code`、校验摘要、`steps_completed`、`email_used`、无密码 |
| T-P2-007 | phase-2 读取 phase-1 留档并调用 `apply_outlook_signup_profile`（符合 requirements §1.3 / §4） | 已完成 | 无留档时 `step=phase2_user_profile`；录入成功时最终 `step=apply_signup_profile`              |

### T-003 子任务（A 方案细化）

| 子任务ID | 内容                                                   | 状态   | 通过标准                                           |
| -------- | ------------------------------------------------------ | ------ | -------------------------------------------------- |
| T-003-1  | 增加序号状态存储 `logs/sequence_state.json` 的读写模块 | 已完成 | `sequence_state.py`                                |
| T-003-2  | 定义序号键维度：`site_name + region + 本机日期`        | 已完成 | `build_sequence_key`                               |
| T-003-3  | 单条创建：成功后序号 +1 并持久化                       | 已完成 | `get_next_sequence` + API 成功后 `commit_sequence` |
| T-003-4  | 批量创建：按顺序分配序号，按成功条目推进序号           | 待办   | 需独立入口或列表配置驱动                           |
| T-003-5  | 覆盖参数：`name_sequence_start` 可人工重置起点         | 已完成 | 配置项 `name_sequence_start` + 状态文件冷启动      |

---

## 四、关键规则落地清单（开发时必须遵守）

- 代理类型固定 `Socks5`
- 浏览器语言固定 `["en", "en-US"]`
- 内核版本固定 `124`
- `region` 必填
- `site_name` 默认 `outlook`
- `name_sequence_start` 默认 `1`，用于初始化或人工覆盖
- 默认由系统自动维护序号（A 方案），避免多次运行重号

---

## 五、任务节奏（避免发散）

- 一次只推进一个最小任务（T-002 -> T-003 -> ...）
- 每完成一项，更新状态与验收结论
- 未完成当前任务前，不跨到下一任务

---

## 六、归档（旧版任务说明）

以下内容对应 **`requirements.md` 的 phase-2`**（浏览器连接、打开注册页、DOM 校验），不是 phase-1。  
当前代码已落地 `connect_browser/open_signup_page/verify_page`；若你发现选择器不稳，可用截图补充信息后继续微调与增强失败用例。
