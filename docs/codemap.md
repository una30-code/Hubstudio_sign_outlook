# 代码与文档映射（Codemap）

> **职责**：`requirements` / `design` 章节 ↔ **源码** ↔ **`tasks.md` 任务** ↔ **`test.md` 用例** 的追溯表。  
> **不包含**：字段字典与 env 键全集——见 `docs/contracts.md`；名词解释——见 `docs/glossary.md`。

---

## 1. 按阶段总览

| 阶段 | `requirements.md` | `design.md`（叙事与边界） | 主要源码 | `tasks.md`（任务 ID 摘要） | `test.md` |
| ---- | ----------------- | ------------------------- | -------- | ------------------------- | --------- |
| phase-0 | §1.1 | §1～§8 | `config.py`、`validate_hubstudio_env_config.py`、`sequence_state.py`、`create_hubstudio_environment.py`、`archive_store.py`、`pipeline.py`、`main.py`、`step_result.py` | T-002～T-009、T-003-1～T-003-5（T-003-4 待办） | TC-P0-001～TC-P0-006 |
| phase-1 | §1.2 | §9 | `outlook_user_profile.py`、`pipeline.py`、`main.py`、`archive_store.py`、`step_result.py` | T-P1-001～T-P1-006 | TC-P1-001～TC-P1-004 |
| phase-2 | §1.3 | §10 | `config.py`（`load_phase2_settings`）、`start_hubstudio_browser.py`、`connect_browser.py`、`open_signup_page.py`、`verify_page.py`、`archive_store.py`、`apply_signup_profile.py`、`ms_hold_challenge.py`、`pipeline.py`、`main.py` | T-P2-001～T-P2-004、T-P2-006、T-P2-007 | TC-P2-001～TC-P2-005 |

---

## 2. phase-0 细粒度映射

| 能力（作用说明） | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ---- | -------- | -------- | -------- | ------- | -------- |
| 配置加载（读取和解析 Hubstudio 环境变量及相关配置文件，供全局使用） | §1.1、§2 | §3、§5.1 | `src/config.py` | T-002 | TC-P0-001、TC-P0-002 |
| 配置校验（检查配置项完整性和规范性，提前发现错误和遗漏） | §1.1 | §5.2 | `src/validate_hubstudio_env_config.py` | T-004 | TC-P0-002 |
| 序号状态管理（A 方案）（保存和更新环境实例的唯一序列号，实现实例唯一性与可追溯） | §1.1 | §8.2 | `src/sequence_state.py`、`src/pipeline.py` | T-003、T-003-1～T-003-5 | TC-P0-003、TC-P0-004 |
| 创建 API 调用（对接 Hubstudio 平台的环境创建接口，完成账号环境分配） | §1.1 | §5.3、§4 | `src/create_hubstudio_environment.py` | T-005 | TC-P0-003～TC-P0-005 |
| 编排与留档（组织 phase-0 各步骤执行顺序，保存关键中间结果留档用于追溯） | §1.1、§2 | §5.4、§7.1 | `src/pipeline.py`、`src/archive_store.py` | T-006、T-009 | TC-P0-003、TC-P0-006 |
| 程序主入口（默认以 phase-0 运行，解析命令行参数，分发主流程调用） | §1.1 | §5 | `src/main.py` | T-006 | TC-P0-003 |
| 独立 API 探测脚本（单独测试 Hubstudio 接口可用性与环境创建流程） | — | §2 | `scripts/test_env_create_api.py` | T-007 | TC-P0-005 |
| 统一结果返回结构（抽象各阶段返回值为标准 StepResult 格式，便于流程编排与错误追溯） | §2 | §6 | `src/step_result.py` | T-006 | TC-P0-003 |

---

## 3. phase-1 细粒度映射

| 能力 | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ---- | -------- | -------- | -------- | ------- | -------- |
| 用户信息与规则 | §1.2 | §9.2 | `src/outlook_user_profile.py` | T-P1-002 | TC-P1-002、TC-P1-003 |
| 冻结 `StepResult` / `data` 键 | §1.2 | §9.3.1 | `src/outlook_user_profile.py`、`src/step_result.py` | T-P1-001 | TC-P1-001 |
| 编排与留档 | §1.2 | §9.3.2 | `src/pipeline.py`、`src/archive_store.py` | T-P1-003、T-P1-006 | TC-P1-001、TC-P1-004 |
| 入口 | §1.2 | §9.4 | `src/main.py` | T-P1-003 | TC-P1-001 |

---

## 4. phase-2 细粒度映射

| 流水线步骤（`step` 语义） | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ------------------------ | -------- | -------- | -------- | ------- | -------- |
| Hubstudio 启停 → CDP 端口 | §1.3 | §10.1、§10.4 | `src/start_hubstudio_browser.py` | T-P2-001 | TC-P2-001、TC-P2-005 |
| CDP 连接 | §1.3 | §10.4 | `src/connect_browser.py` | T-P2-001 | TC-P2-001、TC-P2-005 |
| 打开注册页 | §1.3 | §10.4 | `src/open_signup_page.py` | T-P2-002 | TC-P2-002、TC-P2-005 |
| 页面校验 | §1.3 | §10.4 | `src/verify_page.py` | T-P2-003 | TC-P2-003、TC-P2-005 |
| 读取 phase-1 留档 | §1.3 | §10.4 | `src/archive_store.py` | T-P2-007 | TC-P2-004 |
| 填表与提交 | §1.3 | §10.4 | `src/apply_signup_profile.py` | T-P2-007 | TC-P2-004 |
| phase-2 成功留档 | §1.3 | §10.8 | `src/archive_store.py`、`src/pipeline.py` | T-P2-006 | TC-P2-004 |
| 可选人机长按 | §4（范围外说明） | §10.9 | `src/ms_hold_challenge.py` | — | — |
| phase-2 配置 | §1.3 | §10.3 | `src/config.py` | T-P2-001～T-P2-004 | TC-P2-001～TC-P2-005 |
| 编排与入口 | §1.3 | §10.4 | `src/pipeline.py`、`src/main.py` | T-P2-004 | TC-P2-001～TC-P2-004 |

---

## 5. 自动化测试文件（pytest）

| 覆盖范围 | 路径 |
| -------- | ---- |
| 配置 | `tests/test_config.py` |
| `StepResult` 等 | `tests/test_step_result.py` |
| phase-1 生成规则 | `tests/test_outlook_user_profile.py` |
| archive / 容器相关 | `tests/test_archive_container.py` |

与 `test.md` 手工用例互补；具体命令见 `test.md` §3。

---

## 6. 其他目录（非需求追溯主链）

| 路径 | 说明 |
| ---- | ---- |
| `prompts/` | AI 辅助模板与说明，见 `prompts/README.md` |
| `debug_log.md` | 排障流水记录，不参与需求编号追溯 |
| `design.original.md` | 设计文档历史稿 |

---

## 7. 维护方式

新增或移动源码时：**同步更新本表**与 `docs/contracts.md`（若涉及契约）；`tasks.md` / `test.md` 新增 ID 时在本表加一行或扩展对应格。
