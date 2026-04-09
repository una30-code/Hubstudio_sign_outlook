# 仓库文档与目录地图

> 说明「有什么文件、各自职责、阅读顺序」。**需求条文**以 `requirements.md` 为准；**配置与冻结契约**以 `docs/contracts.md` 为准。

---

## 1. 根目录（工程文档）

| 路径 | 职责 |
| ---- | ---- |
| [requirements.md](requirements.md) | 分阶段目标、功能要求、验收/成功失败定义、范围外；不写全量 env 表 |
| [design.md](design.md) | 各阶段目标与边界、模块协作、phase-2 自动化要点；**关浏览器与会话、人机接续**见 §6.6（单点）；**表格级契约**以 `docs/contracts.md` 为准 |
| [tasks.md](tasks.md) | 任务 ID、状态、优先级；详细文件映射见 [docs/codemap.md](docs/codemap.md) |
| [test.md](test.md) | 用例、命令、期望、产物路径 |
| [debug_log.md](debug_log.md) | 排障记录，非设计规范 |
| [document_map.md](document_map.md) | 本文件：文档索引与职责 |
| [.cursorrules](.cursorrules) | 助手行为与文档阅读顺序 |

---

## 2. `docs/`（契约、术语、映射）

| 路径 | 职责 |
| ---- | ---- |
| [docs/contracts.md](docs/contracts.md) | **StepResult**、留档约定、phase-0/1/2 配置键与冻结接口、Hubstudio 字段映射、phase-2 `step` 与执行顺序 |
| [docs/glossary.md](docs/glossary.md) | CDP、指纹浏览器、archive、phase 编号等专业名词解释 |
| [docs/codemap.md](docs/codemap.md) | requirements/design 章节 ↔ 源码 ↔ tasks ↔ test 追溯表 |

---

## 3. 代码与资源目录（摘要）

| 路径 | 职责 |
| ---- | ---- |
| `src/` | 主程序与流水线实现 |
| `tests/` | pytest |
| `scripts/` | 独立探测脚本（如 Hubstudio API） |
| `prompts/` | Cursor/AI 任务模板，见 `prompts/README.md` |
| `logs/`、`screenshots/`、`test-results/` | 运行时产物（通常不入库或仅本地） |

---

## 4. 推荐阅读顺序（与人协作或改代码前）

1. `requirements.md`  
2. `design.md`  
3. `docs/contracts.md`（改配置、对阶段产物）  
4. `docs/glossary.md`（遇缩写或 Hubstudio/CDP 概念时）  
5. `docs/codemap.md`（定位源码与用例）  
6. `tasks.md`  
7. `test.md`

与 [.cursorrules](.cursorrules) 「文档优先级」一致。
