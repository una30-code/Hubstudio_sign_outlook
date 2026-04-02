# 设计说明（Design）

## 1. 当前阶段目标

通过 Hubstudio 浏览器环境 + Playwright：

打开 Outlook 注册页面，并验证页面加载成功

---

## 2. 技术选型

- Python 3.10+
- Playwright
- 通过 CDP 连接 Hubstudio 浏览器（connect_over_cdp）
- 配置从 `.env` 读取

---

## 3. 模块划分

### 模块1：connect_browser
连接 Hubstudio 浏览器环境

输入：
- CDP 地址（来自 .env）

输出：
- browser / context / page

失败：
- 无法连接
- 浏览器未启动

---

### 模块2：open_signup_page
打开 Outlook 注册页面

输入：
- page
- 注册 URL

输出：
- success: bool
- message: str
- current_url

失败：
- 页面加载失败
- 超时

---

### 模块3：verify_page
验证是否为注册页面

输入：
- page

输出：
- success: bool
- message: str

成功判断（满足任一）：
- URL 正确
- 页面出现注册相关元素（标题/按钮）

失败：
- 页面不正确
- 元素不存在

---

## 4. 执行流程

按顺序执行：

1. connect_browser  
2. open_signup_page  
3. verify_page  

规则：
- 任一步失败 → 停止执行
- 输出错误日志
- 保存截图
- 返回 success = False

---

## 5. 返回结构（统一）

所有模块返回：

```python
{
    "success": True,
    "step": "open_signup_page",
    "message": "xxx",
    "data": {},
    "error": None,
    "screenshot_path": None
}
