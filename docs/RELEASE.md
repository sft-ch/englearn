# 发布与维护说明

面向仓库维护者。普通使用者请看 [部署指南](DEPLOY.md)。

## 1. 发布前检查清单

- [ ] `python scripts/selftest.py` 全部通过
- [ ] `python -m py_compile app.py core/*.py` 无报错
- [ ] `node --check web/app.js`（可选，仅改前端时）
- [ ] `docker compose config --quiet` 通过
- [ ] `config.json`、`data/`、`exports/`、`logs/` 没有被提交
- [ ] README 的功能表与实际情况一致
- [ ] CHANGELOG 已更新，版本号与 `app.py` 里的 `VERSION` 一致
- [ ] 涉及截图的文档没有泄露个人路径或 Key

## 2. 版本号

`app.py` 中的 `VERSION = "0.1.0"` 是唯一事实来源，`/api/health` 会返回它。
发版时同步修改：

1. `app.py` → `VERSION`
2. `CHANGELOG.md` → 新增小节
3. Git tag：`git tag -a v0.1.0 -m "0.1.0"`

## 3. 打 tag 并发布

```bash
git add -A
git commit -m "release: v0.1.0"
git tag -a v0.1.0 -m "Englearn 0.1.0"
git push origin main --tags
```

在 GitHub / Gitee 上基于 tag 创建 Release，说明直接引用 CHANGELOG 对应小节，并附上：

- 运行环境要求（Python 3.10+，Windows 完整体验）
- 升级注意事项（`data/app.db` 会自动迁移，但仍建议先备份）
- 已知问题

## 4. Release Notes 模板

```markdown
## Englearn v0.1.0

### 亮点
- 划词悬浮窗、七段式词汇卡片、句子标记

### 升级方式
- 源码用户：拉取代码后重启 `start.cmd`
- Docker 用户：`docker compose pull && docker compose up -d`

### 兼容性
- Windows 10/11 完整功能；Linux/macOS/Docker 为网页模式
- 数据库自动迁移，无需手动操作
```

## 5. 许可证

仓库使用 **MIT**（见 `LICENSE`）。选择理由：

- 个人工具类项目，希望使用者能自由修改、二次分发
- 不引入传染性约束，方便被其他项目引用

如需更换：

- **Apache-2.0**：需要专利授权条款时
- **GPL-3.0**：希望衍生作品也必须开源时

更换后需同步 README 的许可证小节与 Release 说明。

## 6. 依赖与安全

- 运行时零第三方依赖，减少供应链风险
- `config.json` 含明文 API Key，已加入 `.gitignore`
- 提交前可用 `git status` 确认没有 `config.json`、`data/`、`logs/`
- 若误提交了 Key：立即在服务商后台吊销并重新生成，再考虑用 `git filter-repo` 清理历史

## 7. 贡献与协作

建议补充以下文件（当前未提供，可按需添加）：

- `.github/ISSUE_TEMPLATE/bug_report.md`：系统版本、Python 版本、复现步骤、`logs/error.log` 片段
- `.github/pull_request_template.md`：改动说明、自测方式（`scripts/selftest.py` 通过）
- `.github/workflows/ci.yml`：在 `windows-latest` 与 `ubuntu-latest` 上跑 `python scripts/selftest.py`

CI 示例：

```yaml
name: ci
on: [push, pull_request]
jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python scripts/selftest.py
```

## 8. 目录约定

```text
app.py                入口（HTTP + 热键 + 悬浮窗调度）
core/                 纯逻辑模块，不依赖 web/
web/                  前端静态资源
scripts/              开发、测试、文档工具（不进容器镜像）
docs/                 部署、发布、教程文档
data/ exports/ logs/  运行期产物（git 忽略）
```
