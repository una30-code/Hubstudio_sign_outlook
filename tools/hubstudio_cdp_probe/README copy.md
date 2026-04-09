# Hubstudio CDP 地址探测（隔离目录）

用于验证：**同一环境 ID** 在多次 `browser/stop` → `browser/start` 后，返回的 **`debuggingPort` / CDP HTTP 基址是否变化**。

- **不写入** 仓库根目录的 `logs/`、`screenshots/`、`.env`。
- 结果仅写入本目录下的 `output/`（已 `.gitignore`）。

## 前置条件

- Hubstudio 本机 API 可达（与主项目相同，默认 `http://127.0.0.1:6873`）。
- 已知有效的 **环境 ID**（`containerCode`）。
- 建议在项目虚拟环境中执行（已安装依赖即可，无需额外包）。

## 用法

在**仓库根目录**执行（保证 `src` 可导入）：

```powershell
# 从 .env 读取 HUBSTUDIO_API_BASE（可选）
$env:PYTHONPATH = "."
python tools/hubstudio_cdp_probe/run_probe.py --container-code <你的环境ID> --rounds 5
```

或显式指定 API 根地址：

```powershell
$env:PYTHONPATH = "."
python tools/hubstudio_cdp_probe/run_probe.py --api-base http://127.0.0.1:6873 --container-code <你的环境ID> --rounds 5
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--container-code` | 必填，Hubstudio 环境 ID |
| `--rounds` | 循环次数，每次先 best-effort `stop` 再 `start`（默认 3） |
| `--api-base` | 可选；缺省读环境变量 `HUBSTUDIO_API_BASE` |
| `--sleep` | 每轮间隔秒数，便于你观察浏览器（默认 2，设 0 关闭） |
| `--no-dotenv` | 不加载仓库根目录 `.env` |

## 输出

- `tools/hubstudio_cdp_probe/output/probe_<UTC时间>.jsonl`：每行一轮记录的 JSON。
- 控制台打印摘要：每轮端口、相邻轮是否变化、去重后的端口集合。

## 说明

每次调用与主项目 phase-2 默认策略一致：**best-effort stop → start**，从 `start` 响应读取 `debuggingPort`。若 Hub 行为变更，以实际响应为准。
