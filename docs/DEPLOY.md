# Englearn 部署指南

从零开始，把 Englearn 跑起来。三种方式任选其一：

| 方式 | 适用场景 | 功能完整度 | 验证状态 |
| --- | --- | --- | --- |
| A. Windows 双击 `start.cmd` | 日常使用（推荐） | 完整：悬浮窗 + 全局热键 + 剪贴板 | ✅ 已验证 |
| B. `run.sh`（Linux / macOS） | 只想用网页界面 | 仅网页：粘贴 / 手动取词 | ⚠️ 未实测 |
| C. Docker / Compose | 服务器、NAS、隔离环境 | 仅网页 | ✅ 已验证（构建 + 启动 + 分析） |

> 划词悬浮窗、全局热键、模拟 Ctrl+C 取词都依赖 Win32 API，**只有 Windows 能用**。
> Linux / macOS / 容器里是「浏览器 + 手动粘贴」的网页版。

---

## 1. 前置条件

- **Python 3.10 或更高**（推荐 3.12）。仓库**没有任何第三方运行时依赖**，不需要 `pip install`。
- 一个 OpenAI 兼容的模型服务 API Key。默认对接 DeepSeek，也可以是 OpenAI、MiniMax 等。
- 磁盘约 100 MB（含 Python 运行时之外的数据）。

检查 Python：

```bash
python --version     # Windows
python3 --version    # Linux / macOS
```

期望输出类似 `Python 3.12.14`。低于 3.10 会因语法不兼容直接报错。

---

## 2. 方式 A：Windows 源码直跑（功能最全）

### 2.1 获取代码

```bash
git clone <你的仓库地址> Englearn
cd Englearn
```

或直接下载 ZIP 解压，目录结构应包含 `app.py`、`core/`、`web/`、`start.cmd`。

### 2.2 启动

双击 `start.cmd`。脚本会依次在 PATH、`py` 启动器、常见安装目录中查找 Python。

预期输出：

```
  [Englearn] interpreter: python
========================================================
  Englearn v0.1.0 已启动
  地址：http://127.0.0.1:8765
  模式：真实模型　模型：deepseek-chat
  关闭本窗口或按 Ctrl+C 即可退出
========================================================
  热键：alt+d（选中英文后按下取词）
  划词：选中英文后鼠标旁会弹出操作窗，点窗外或 Esc 关闭
```

首次启动会自动生成 `config.json`（含空 Key）。

### 2.3 验证

浏览器应自动打开 `http://127.0.0.1:8765`。也可以命令行验证：

```bash
curl http://127.0.0.1:8765/api/health
```

期望返回 `"ok": true` 与 `"version": "0.1.0"`。

### 2.4 配置 Key

页面右上角 **设置** → 填 API Key → 保存。顶栏会从「未配置 API Key」变成「已连接 · deepseek-chat」。

暂时没有 Key 时，可在设置里勾选 **Mock 演示模式**，用示例数据走通界面。

### 2.5 开机自启（可选）

设置里勾选「开机自动启动」。原理是写入
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，指向 `scripts\start-hidden.vbs`，
登录后静默启动并打开页面，不需要管理员权限。取消勾选即移除。

---

## 3. 方式 B：Linux / macOS 源码直跑

```bash
chmod +x run.sh
./run.sh
```

脚本等价于 `python3 app.py --no-popup`，会打印访问地址（默认 8765）。

> 该平台没有桌面悬浮窗与全局热键，使用方式是：把英文粘贴进输入框，或点页面上的「取选区」按钮。

---

## 4. 方式 C：Docker（网页模式）

### 4.1 启动

```bash
docker compose up -d
docker compose logs -f      # 看到 "Englearn v0.1.0 已启动" 即可
```

访问 <http://127.0.0.1:8765>。

> 若宿主机 8765 已被占用（例如 Windows 桌面版正在运行），用环境变量换端口：
> `ENGL_PORT=8899 docker compose up -d`，然后访问 `http://127.0.0.1:8899`。
> 注意容器与桌面版**共用同一个 `data/app.db`**，同时运行会让两边数据混在一起，
> 建议二选一，或给容器单独指定数据目录。

### 4.2 目录与配置

Compose 会挂载三个宿主机目录：

| 宿主机 | 容器内 | 内容 |
| --- | --- | --- |
| `./data` | `/app/data` | SQLite 数据库 |
| `./exports` | `/app/exports` | 导出的 md/json/csv/anki/html |
| `./config` | `/app/config` | `config.json`（含 API Key） |

首次启动后 `./config/config.json` 会自动生成。可以直接编辑它填 Key：

```json
{
  "llm": { "base_url": "https://api.deepseek.com", "model": "deepseek-chat", "api_key": "sk-..." }
}
```

改完 `docker compose restart`。在网页设置里保存也会写回这个文件。

### 4.3 验证

```bash
curl http://127.0.0.1:8765/api/health
docker compose ps          # 状态应为 healthy
```

### 4.4 停止与清理

```bash
docker compose down          # 停止，保留数据
docker compose down -v       # 连卷一起删（数据在宿主机目录，需自行删除）
```

### 4.5 拉不到基础镜像时

Docker Hub 在部分地区不可直连，可先拉镜像再构建：

```bash
docker pull docker.m.daocloud.io/library/python:3.12-slim
docker tag  docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim
docker compose up -d --build
```

---

## 5. 配置项

`config.json`（首次启动自动生成，Windows 与容器同名）：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `host` | `127.0.0.1` | 监听地址，本机使用不要改 |
| `port` | `8765` | 被占用时自动向后尝试 10 个端口 |
| `hotkey` | `alt+d` | 取词热键，冲突时自动降级到备选组合 |
| `clipboard_watch` | `false` | 监听剪贴板，手动 Ctrl+C 也触发 |
| `select_popup` | `true` | 选中英文弹出悬浮窗（仅 Windows） |
| `max_chars` | `4000` | 单次分析文本上限 |
| `mock` | `false` | 演示模式，不调用模型 |
| `llm.base_url` | `https://api.deepseek.com` | 任意 OpenAI 兼容地址 |
| `llm.model` | `deepseek-chat` | 模型名 |
| `llm.api_key` | 空 | **敏感信息**，已被 `.gitignore` 忽略 |
| `llm.timeout` | `60` | 请求超时秒数 |

环境变量（可选，主要用于多实例与测试）：

| 变量 | 作用 |
| --- | --- |
| `ENGL_CONFIG` | 指定另一份 `config.json` 路径 |
| `ENGL_DATA_DIR` | 指定另一个数据目录（数据库就在里面） |
| `ENGL_PY` | Windows 上指定 `python.exe` 绝对路径（路径不含空格） |

---

## 6. 完整验证清单

不接模型、不花钱，验证部署是否成功：

```bash
python scripts/selftest.py
```

期望输出：

```
  PASS  health
  PASS  index page
  PASS  word card fields
  PASS  sentence structure
  PASS  save word
  PASS  sentence marks
  PASS  list sentences
  PASS  day view
  PASS  export markdown
  PASS  export includes marks
  PASS  export other formats

11/11 项通过
```

该脚本会自己在临时目录拉起一个 mock 服务，跑完自动关闭，不碰你的真实数据。

---

## 7. 数据与备份

| 路径 | 内容 | 备份建议 |
| --- | --- | --- |
| `data/app.db` | 生词、句子、标记、历史记录 | 定期复制 |
| `exports/` | 导出文件 | 可再生成 |
| `config.json` | 含 API Key | 单独保存，勿公开 |
| `logs/` | `server.log`、`error.log` | 排查用 |

备份 = 停服务后复制 `data/` 与 `config.json`。数据库是单文件 SQLite，直接复制即可。

---

## 8. 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 双击后窗口一闪而过 | 没找到 Python | 安装 Python 3.10+ 并勾选 PATH；或设 `ENGL_PY` |
| 浏览器白屏 | 打开早于服务就绪 | 刷新；地址以控制台为准 |
| 端口打不开 | 控制台被关掉 | 重新启动，别关黑窗口 |
| `Unauthorized` / 401 | Key 无效 | 检查 Key 与 `base_url` 是否配套 |
| 502 / 超时 | 网络或代理 | 检查出网；可先用 Mock 模式验证功能 |
| 热键无反应 | 被其他程序占用 | 看顶栏显示的实际热键，或到设置里换 |
| 选中不弹窗 | 安全软件拦截全局钩子 | 看 `logs/error.log`，或 `--no-popup` 退回页面模式 |
| 容器启动即退出 | 端口冲突 / 配置写错 | `docker compose logs` 看输出 |
| 中文乱码（控制台） | 代码页问题 | `start.cmd` 已包含 `chcp 65001`；容器一般无此问题 |

---

## 9. 已知限制

- **平台**：悬浮窗、全局热键、模拟复制仅 Windows；Linux / macOS 未实测，仅网页可用。
- **鉴权**：单用户本地工具，**没有任何登录或权限校验**。绝对不要把端口暴露到公网或不可信局域网。
- **剪贴板**：取词会临时占用剪贴板，结束后只还原**文本**，原本的图片/文件会丢失。
- **输出**：模型调用为一次性返回，暂未实现流式逐字输出。
- **数据**：SQLite 单文件，适合个人量级；多人共享请自行迁移到服务端方案。
- **Key 存储**：`config.json` 中是明文，注意文件权限与备份泄露风险。

---

## 10. 卸载

1. Windows：设置里取消「开机自动启动」；删除整个项目目录即可。
2. 确认没有残留进程：任务管理器结束 `python.exe`。
3. Docker：`docker compose down`，再删除项目目录与镜像 `docker rmi englearn:0.1.0`。
