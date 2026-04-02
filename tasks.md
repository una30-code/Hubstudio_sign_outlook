# 任务列表（Tasks）

> 按优先级执行；完成一项再开下一项。状态：`待办` / `进行中` / `已完成` / `阻塞`。  
> **当前目标（MVP）**：仅完成 **Hubstudio 环境创建**（对应 `requirements.md` 的 phase-0），不展开页面自动化与注册流程。

## 一、MVP 任务范围（仅环境创建）

本轮只交付以下能力闭环：

1. 读取环境创建配置（含 `.env` 与 `hubstudio_env_create_config`）
2. 校验字段与命名规则（`site_name` + 序号 + `region` + 本机日期）
3. 调用 `POST /api/v1/env/create` 创建 Hubstudio 环境
4. 返回统一结构化结果（`success/message/data/error/screenshot_path`）
5. 记录关键日志并支持失败排查

明确不做：

- 不连接浏览器 CDP
- 不打开 Outlook 页面
- 不执行页面交互或注册流程

---

## 二、模块与文件映射（MVP）

| 顺序 | 模块 | 建议源码文件 | 目的 |
|------|------|--------------|------|
| 1 | 配置读取 | `src/config.py` | 读取 `.env` 与创建配置，输出标准化参数 |
| 2 | 字段校验 | `src/validate_hubstudio_env_config.py` | 校验必填字段、类型、范围、命名规则 |
| 3 | 名称生成 | `src/environment_name.py` | 统一生成 `containerName`（含起始序号规则） |
| 4 | API 调用 | `src/create_hubstudio_environment.py` | 组装请求体并调用 `/api/v1/env/create` |
| 5 | 编排入口 | `src/pipeline.py` | 串联 load -> validate -> create，输出统一结果 |
| 6 | 程序入口 | `src/main.py` | 触发编排、输出日志、设置退出码 |

说明：文件名可按现有工程微调，但函数命名保持业务语义（`hubstudio_env_*`）。

---

## 三、当前迭代任务（按执行顺序）

| ID | 任务 | 状态 | 验收标准 |
|----|------|------|----------|
| T-001 | 对齐文档基线：`requirements.md` + `design.md` + 本任务清单一致 | 已完成 | 三份文档均以“Hubstudio 环境创建”作为当前目标 |
| T-002 | 实现配置模型与读取逻辑（`.env` + `hubstudio_env_create_config`） | 待办 | 成功读取 `HUBSTUDIO_API_BASE`、`site_name`、`region`、`name_sequence_start`、代理字段 |
| T-003 | 实现命名规则与序号策略（A 方案） | 待办 | 单条与批量均按 `{site_name}{seq}_{region}_{YYYY年M月D日}`；`seq` 由状态文件自动递增，支持 `name_sequence_start` 覆盖 |
| T-004 | 实现字段校验逻辑 | 待办 | 缺失/非法字段可返回可读错误；命名不符合规则时返回失败 |
| T-005 | 实现 Hubstudio 创建接口调用 | 待办 | 成功调用 `/api/v1/env/create` 并解析 `containerCode` |
| T-006 | 实现编排与统一返回结构 | 待办 | 最终返回包含 `success/step/message/data/error/screenshot_path` |
| T-007 | 增加最小可用验证（手工或脚本） | 待办 | 至少覆盖：成功创建、代理格式错误、API 不可达三类结果 |
| T-008 | 更新测试文档与排障记录（仅 phase-0） | 待办 | `test.md` 与 `debug_log.md` 可支撑 phase-0 验收与定位 |

### T-003 子任务（A 方案细化）

| 子任务ID | 内容 | 状态 | 通过标准 |
|----------|------|------|----------|
| T-003-1 | 增加序号状态存储 `logs/sequence_state.json` 的读写模块 | 待办 | 文件不存在可自动初始化，存在可正确读取 |
| T-003-2 | 定义序号键维度：`site_name + region + 本机日期` | 待办 | 不同地区/日期互不干扰 |
| T-003-3 | 单条创建：成功后序号 +1 并持久化 | 待办 | 连续运行两次，序号连续递增 |
| T-003-4 | 批量创建：按顺序分配序号，按成功条目推进序号 | 待办 | 部分失败时，后续运行不回退已成功条目序号 |
| T-003-5 | 覆盖参数：`name_sequence_start` 可人工重置起点 | 待办 | 覆盖后立即生效并写回状态文件 |

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

以下内容已从当前迭代移出：Phase 1 页面自动化（`connect_browser`、`open_signup_page`、`verify_page`）。  
后续仅在你确认开启 phase-2 时再恢复对应任务。

