# 测试说明（Test）

> 测试策略、用例、通过条件与产物位置。  
> **当前范围**：`requirements.md` **phase-0**（Hubstudio 环境创建） + **phase-1**（Outlook 注册用用户信息生成） + **phase-2**（连接 CDP + 打开 Outlook 注册页 + DOM 校验）。

## 1. 测试类型


| 类型        | 工具/方式                                     | 说明                                                      |
| --------- | ----------------------------------------- | ------------------------------------------------------- |
| 手工冒烟      | 指人工操作、快速覆盖主要流程，验证系统最基本功能是否正常，无须细致验证所有边界情况 | 例如依照第2节用例，直接运行程序，观察主要结果，确认无重大报错                         |
| 独立 API 探测 | `python scripts/test_env_create_api.py`   | 最小请求体（如「不使用代理」），与主流程解耦，用于区分「代码问题」与「本机 connector 问题」     |
| 自动化（可选）   | pytest                                    | 可对 `load_hubstudio_env_create_config` 等做纯单元测试；**当前未强制** |


## 2. 用例表（phase-0）


| ID        | 名称             | 映射            | 前置条件                                                               | 步骤摘要                                                                                                                                                                                                                                                                  | 期望结果                                                                                                                |
| --------- | -------------- | ------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| TC-P0-001 | 配置加载成功         | T-002         | `.env` 含 `HUBSTUDIO_API_BASE`、`REGION`、代理（`PROXY_RAW` 或 `PROXY_*`） | 在项目根目录：`$env:PYTHONPATH="src"; python -c "from config import load_hubstudio_env_create_config; load_hubstudio_env_create_config()"`（Linux/macOS：`PYTHONPATH=src python -c "from config import load_hubstudio_env_create_config; load_hubstudio_env_create_config()"`） | 无异常，返回 `HubstudioEnvCreateConfig`                                                                                   |
| TC-P0-002 | 配置缺必填项         | T-002 / T-004 | 临时去掉 `REGION` 或代理                                                  | 同上命令                                                                                                                                                                                                                                                                  | 抛出 `ValueError` 或校验失败信息可读                                                                                           |
| TC-P0-003 | 主流程创建成功        | T-005～T-006   | connector 正常、API 可达                                                | 运行 `python src/main.py` 或调试 `src/main.py`                                                                                                                                                                                                                             | `success=True`；`data` 含 `container_code`、`environment_name`；`logs/phase0.log` 有记录；`logs/sequence_state.json` 在成功后推进 |
| TC-P0-004 | API 不可达 / 业务失败 | T-005         | 故意错误 `HUBSTUDIO_API_BASE` 或 connector 未启                           | 运行 `src/main.py`                                                                                                                                                                                                                                                      | `success=False`；`error` 非空；进程退出码非 0；**序号不应在失败路径被提交**（见 `sequence_state` 设计）                                         |
| TC-P0-005 | 独立脚本探测         | T-007         | 与 TC-P0-003 相同网络环境                                                 | `python scripts/test_env_create_api.py`                                                                                                                                                                                                                               | 返回 HTTP 200 且 JSON `code=0`（脚本打印体可见）；用于与主流程对照                                                                       |
| TC-P0-006 | phase-0 留档可追溯      | T-009         | TC-P0-003 已通过                                                          | 执行主流程后检查 archive 位置或引用（`archive_path`/`archive_ref`）                                                                                                                                                                                                       | 可查询到本次创建记录，至少含 `containerCode/environment_name/created_at/success`                                                   |


负例细节可在 `debug_log.md` 留一条可追溯记录。

## 3. 用例表（phase-1）


| ID        | 名称             | 映射       | 前置条件                  | 步骤摘要                                                                                                                                                                                                                         | 期望结果                                                                                             |
| --------- | -------------- | -------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| TC-P1-001 | phase-1 基础生成   | T-P1-002 | 可选：设置 `USER_GEN_SEED` | `python src/main.py --phase1`                                                                                                                                                                                                | 进程退出码为 0；`logs/phase1.log` 包含 `success=True step=outlook_user_profile`；日志里 `password` 被脱敏为 `***` |
| TC-P1-002 | 规则校验（生日/账号/密码） | T-P1-002 | 可选：seed 固定，便于复现       | `python -c "from src.outlook_user_profile import generate_outlook_user_profile; from datetime import date; p=generate_outlook_user_profile(seed=123, reference_date=date(2026,4,2)); print(p.account); print(p.birth_date)"` | 生日年龄在 18~55（含边界）；账号末尾 5 位数字；密码长度 10 且包含数字/小写/大写                                                  |
| TC-P1-003 | 单元测试回归         | T-P1-002 | pytest 环境就绪           | `pytest -q tests/test_outlook_user_profile.py`                                                                                                                                                                               | 全部用例通过                                                                                           |
| TC-P1-004 | phase-1 留档可追溯      | T-P1-006 | TC-P1-001 已通过         | 执行 `python src/main.py --phase1` 后检查 archive 位置或引用                                                                                                                                                                                                                  | 可查询到本次生成记录，含 `first_name/last_name/birth_date/account/generated_at/success` |


## 4. 用例表（phase-2）


| ID        | 名称             | 映射                               | 前置条件                                                  | 步骤摘要                          | 期望结果                                                    |
| --------- | -------------- | -------------------------------- | ----------------------------------------------------- | ----------------------------- | ------------------------------------------------------- |
| TC-P2-001 | 开环境 + CDP 就绪   | `hubstudio_browser_start` / `connect_browser` | 默认：`HUBSTUDIO_API_BASE` + `HUBSTUDIO_CONTAINER`（或留档中有 containerCode）；或仅设 `HUBSTUDIO_CDP_URL` 跳过 stop/start | `python src/main.py --phase2` | 默认路径：best-effort `browser/stop` 后 `browser/start` 成功；`step=connect_browser success=True` |
| TC-P2-002 | 打开 Outlook 注册页 | `open_signup_page`               | TC-P2-001 通过；`OUTLOOK_REGISTER_URL` 可达                | 同上                            | `step=open_signup_page success=True` 且返回 `current_url`  |
| TC-P2-003 | DOM 校验通过       | `verify_page`                    | 页面加载完成                                                | 同上                            | `step=verify_page success=True`（URL 匹配或注册相关元素命中任一）      |
| TC-P2-004 | 端到端成功          | `pipeline`                       | TC-P2-001~003 可全部满足                                   | 同上                            | 总体返回 `success=True`                                     |
| TC-P2-005 | 失败截图可追溯        | `open_signup_page / verify_page` | 故意错误环境 ID、`HUBSTUDIO_CDP_URL` 或 `OUTLOOK_REGISTER_URL` | 同上                            | `success=False`；`hubstudio_browser_start` / `connect` 失败无页截图；open/verify 失败尽量有 `screenshot_path` |


## 5. 产物与报告

- **运行日志**：`logs/phase0.log`（phase-0） / `logs/phase1.log`（phase-1） / `logs/phase2.log`（phase-2）
- **archive 留档目录**：`logs/archive/`（建议 JSONL；按 phase 与日期分文件）
- **序号状态**：`logs/sequence_state.json`（仅创建成功后会 `commit`）
- **失败截图**：phase-2（open/verify）失败时建议必有；失败截图目录 `screenshots/`
- **测试框架产出**：可放在 `test-results/`（如后续加 pytest）

## 6. 通过 / 发布门槛

- **必须**：在目标环境上 **TC-P0-003** 通过（或等价手工签字），且返回结构与 `design.md` 统一返回字段一致。
- **必须**：在目标环境上 **TC-P0-006** 通过（或等价手工签字）。
- **必须**：在目标环境上 **TC-P1-001/TC-P1-003** 通过（或等价手工签字）。
- **必须**：在目标环境上 **TC-P1-004** 通过（或等价手工签字）。
- **必须**：在目标环境上 **TC-P2-001~TC-P2-004** 通过（或等价手工签字）。
- **建议**：**TC-P0-004** 至少验证一次；**TC-P0-005** 在排障时优先执行以隔离 connector。

## 7. 变更记录


| 日期         | 变更摘要                                              |
| ---------- | ------------------------------------------------- |
| （初始化骨架）    | 文档创建                                              |
| 2026-03-20 | 旧版：对齐 Phase 1（CDP / 注册页）                          |
| 2026-04-02 | 重写为 phase-0：环境创建、独立脚本、与 `tasks.md` T-007/T-008 一致 |


