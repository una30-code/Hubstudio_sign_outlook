# 代码与文档映射（Codemap）

> **职责**：`requirements` / `design` 章节 ↔ **源码** ↔ **`tasks.md` 任务** ↔ **`test.md` 用例** 的追溯表。  
> **不包含**：字段字典与 env 键全集——见 `docs/contracts.md`；名词解释——见 `docs/glossary.md`。

---

## 1. 按阶段总览

| 阶段 | `requirements.md` | `design.md`（叙事与边界） | 主要源码 | `tasks.md`（任务 ID 摘要） | `test.md` |
| ---- | ----------------- | ------------------------- | -------- | ------------------------- | --------- |
| phase-0 | §1.1 | §1～§4 | `config.py`、`validate_hubstudio_env_config.py`、`sequence_state.py`、`create_hubstudio_environment.py`、`archive_store.py`、`pipeline.py`、`main.py`、`step_result.py` | T-002～T-009、T-003-1～T-003-5（T-003-4 待办） | TC-P0-001～TC-P0-006 |
| phase-1 | §1.2 | §5 | `outlook_user_profile.py`、`pipeline.py`、`main.py`、`archive_store.py`、`step_result.py` | T-P1-001～T-P1-006 | TC-P1-001～TC-P1-004 |
| phase-2 | §1.3 | §6 | `config.py`（`load_phase2_settings`）、`start_hubstudio_browser.py`、`connect_browser.py`、`open_signup_page.py`、`verify_page.py`、`archive_store.py`、`apply_signup_profile.py`、`ms_hold_challenge.py`、`pipeline.py`、`main.py` | T-P2-001～T-P2-004、T-P2-006、T-P2-007 | TC-P2-001～TC-P2-005 |

---

## 2. phase-0 细粒度映射

| 能力（作用说明） | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ---- | -------- | -------- | -------- | ------- | -------- |
| 配置加载 | §1.1、§2 | §3 | `src/config.py` | T-002 | TC-P0-001、TC-P0-002 |
| 配置校验 | §1.1 | §3 | `src/validate_hubstudio_env_config.py` | T-004 | TC-P0-002 |
| 序号状态（A 方案） | §1.1 | §3（命名规则见 `contracts` §3.6） | `src/sequence_state.py`、`src/pipeline.py` | T-003、T-003-1～T-003-5 | TC-P0-003、TC-P0-004 |
| 创建 API | §1.1 | §3 | `src/create_hubstudio_environment.py` | T-005 | TC-P0-003～TC-P0-005 |
| 编排与留档 | §1.1、§2 | §3、§4 | `src/pipeline.py`、`src/archive_store.py` | T-006、T-009 | TC-P0-003、TC-P0-006 |
| 程序入口（默认 phase-0） | §1.1 | §3 | `src/main.py` | T-006 | TC-P0-003 |
| 独立 API 探测脚本 | — | §2 | `scripts/test_env_create_api.py` | T-007 | TC-P0-005 |
| 统一 `StepResult` | §2 | §3、`contracts` §1 | `src/step_result.py` | T-006 | TC-P0-003 |

---

## 3. phase-1 细粒度映射

| 能力 | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ---- | -------- | -------- | -------- | ------- | -------- |
| 用户信息与规则 | §1.2 | §5、`contracts` §4 | `src/outlook_user_profile.py` | T-P1-002 | TC-P1-002、TC-P1-003 |
| 冻结 `StepResult` / `data` 键 | §1.2 | §5、`contracts` §4 | `src/outlook_user_profile.py`、`src/step_result.py` | T-P1-001 | TC-P1-001 |
| 编排与留档 | §1.2 | §5 | `src/pipeline.py`、`src/archive_store.py` | T-P1-003、T-P1-006 | TC-P1-001、TC-P1-004 |
| 入口 | §1.2 | §5 | `src/main.py` | T-P1-003 | TC-P1-001 |

---

## 4. phase-2 细粒度映射

| 流水线步骤（`step` 语义） | 需求锚点 | 设计锚点 | 源码文件 | 任务 ID | 测试用例 |
| ------------------------ | -------- | -------- | -------- | ------- | -------- |
| Hubstudio 启停 → CDP 端口 | §1.3 | §6.1、`contracts` §5.4 | `src/start_hubstudio_browser.py` | T-P2-001 | TC-P2-001、TC-P2-005 |
| CDP 连接 | §1.3 | §6、`contracts` §5.4 | `src/connect_browser.py` | T-P2-001 | TC-P2-001、TC-P2-005 |
| 打开注册页 | §1.3 | §6、`contracts` §5.4 | `src/open_signup_page.py` | T-P2-002 | TC-P2-002、TC-P2-005 |
| 页面校验 | §1.3 | §6.3、`contracts` §5.4 | `src/verify_page.py` | T-P2-003 | TC-P2-003、TC-P2-005 |
| 读取 phase-1 留档 | §1.3 | §6、`contracts` §5.4 | `src/archive_store.py` | T-P2-007 | TC-P2-004 |
| 填表与提交 | §1.3 | §6.3、`contracts` §5.4 | `src/apply_signup_profile.py` | T-P2-007 | TC-P2-004 |
| phase-2 成功留档 | §1.3 | §6.3、`contracts` §2.3 | `src/archive_store.py`、`src/pipeline.py` | T-P2-006 | TC-P2-004 |
| 可选人机长按 | §4（范围外说明） | §6.5、`contracts` §5.3 | `src/ms_hold_challenge.py` | — | — |
| phase-2 配置 | §1.3 | §6.2、`contracts` §5.2 | `src/config.py` | T-P2-001～T-P2-004 | TC-P2-001～TC-P2-005 |
| 编排与入口 | §1.3 | §6、`contracts` §5.4 | `src/pipeline.py`、`src/main.py` | T-P2-004 | TC-P2-001～TC-P2-004 |

---

## 5. 自动化测试文件（pytest）

| 覆盖范围 | 路径 |
| -------- | ---- |
| 配置 | `tests/test_config.py` |
| `StepResult` 等 | `tests/test_step_result.py` |
| phase-1 生成规则 | `tests/test_outlook_user_profile.py` |
| archive / 容器相关 | `tests/test_archive_container.py` |
| `ms_hold_challenge`（人机页检测 Mock + 模拟页长按） | `tests/test_ms_hold_challenge.py`（对应 `test.md` TC-P2-006） |

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
