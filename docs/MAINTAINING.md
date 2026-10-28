# 仓库维护手册

面向 Englearn 的日常维护者。发布相关的规范见 [RELEASE.md](RELEASE.md)，部署见 [DEPLOY.md](DEPLOY.md)。

---

## 0. 一次性准备（已完成，换机器时用）

```powershell
git config user.name  "sft-ch"
git config user.email "sft-ch@users.noreply.github.com"
git remote -v                                   # 应指向 github.com/sft-ch/englearn
gh auth status                                  # 应显示 Logged in to github.com
```

`gh` 的安装位置：`%LOCALAPPDATA%\Programs\gh\bin\gh.exe`（已加入用户 PATH）。
若推送时出现连接重置：

```powershell
git config http.version HTTP/1.1
git config http.postBuffer 524288000
```

---

## 1. 日常改动循环

```powershell
cd D:\tools\dsh\English_learn

# 1) 改代码（web/ 改完刷新页面即可；core/、app.py 改完要重启服务）

# 2) 本地验证——这一步不要省
python -m compileall -q app.py core
python scripts/selftest.py          # 期望：15/15 项通过

# 3) 看自己改了什么
git status
git diff

# 4) 提交
git add -A
git commit -m "feat(words): 生词本按类别筛选"

# 5) 推送（会自动触发 CI）
git push
```

**改完后端要重启服务**（当前是开机自启的隐藏进程）：

```powershell
$line = netstat -ano | Select-String ":8765\s+.*LISTENING" | Select-Object -First 1
if ($line) { Stop-Process -Id ([int](($line.ToString().Trim() -split "\s+")[-1])) -Force }
Start-Process wscript.exe -ArgumentList '"D:\tools\dsh\English_learn\scripts\start-hidden.vbs"'
```

---

## 2. 提交信息规范

`类型(范围): 中文描述`，一次提交只做一件事。

| 类型 | 用途 | 示例 |
| --- | --- | --- |
| `feat` | 新功能 | `feat(words): 生词按单词/短语/短句分类` |
| `fix` | 修 bug | `fix(ci): selftest 输出改用 UTF-8` |
| `docs` | 文档 | `docs: 更新部署指南端口说明` |
| `refactor` | 重构，不改行为 | `refactor(store): 拆分迁移逻辑` |
| `test` | 测试 | `test: 增加导出格式用例` |
| `chore` | 杂项 | `chore: 升级 gh 版本` |

写清楚**为什么**改，比写清楚改了什么更有价值。

---

## 3. 分支策略

- **小改动**（文档、文案、单行修复）：直接推 `main`。
- **较大改动**（新功能、重构）：开分支 + PR，CI 通过再合并。

```powershell
git switch -c feat/vocab-tags
# …改代码、提交…
git push -u origin feat/vocab-tags
gh pr create --fill            # 用提交信息生成 PR
gh pr checks                   # 看 CI
gh pr merge --squash --delete-branch
```

合并后本地同步：

```powershell
git switch main
git pull --rebase
```

---

## 4. 发版

以「生词分类」这个待发布功能为例，升到 `0.2.0`：

1. 改 `app.py` 里的 `VERSION = "0.2.0"`
2. 改 `CHANGELOG.md`：把 `## [未发布]` 改成 `## [0.2.0] - 2026-10-28`
3. 提交并推送
4. 打标签
5. 建 Release

```powershell
git add -A
git commit -m "chore(release): v0.2.0"
git push

git tag -a v0.2.0 -m "Englearn v0.2.0"
git push origin v0.2.0

# 从 CHANGELOG 自动截取该版本说明
python -c "import re,pathlib;t=pathlib.Path('CHANGELOG.md').read_text(encoding='utf-8');m=re.search(r'## \[0\.2\.0\].*?(?=\n## |\Z)',t,re.S);pathlib.Path('notes.md').write_text(m.group(0),encoding='utf-8')"
gh release create v0.2.0 --title "Englearn v0.2.0" --notes-file notes.md
Remove-Item notes.md
```

验证：

```powershell
gh release view v0.2.0
```

**不要**图省事用 `git push -f` 移动已发布的 tag——已经有人下载过就对不上了。改错了就发新版本。

---

## 5. 查看与处理 CI

```powershell
gh run list --limit 5            # 最近几次
gh run watch <run-id>            # 实时等结果
gh run view <run-id> --log-failed  # 只看失败步骤的日志
gh run rerun <run-id>            # 重跑（偶发网络问题）
```

当前 CI 覆盖：`ubuntu/windows × py3.10/3.12` 跑冒烟测试，另有一个 Docker 构建与容器健康检查任务。

常见失败原因：

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| `UnicodeEncodeError` | Windows runner 默认 cp1252 | 输出前 `sys.stdout.reconfigure(encoding="utf-8")` |
| 找不到文件 | 路径大小写 / 分隔符 | 用 `pathlib`、相对仓库根目录 |
| Docker 拉取失败 | 网络受限 | 换基础镜像源或改用缓存 |

---

## 6. 回滚

```powershell
git revert <sha>        # 推荐：生成一个反向提交，历史保留
git reset --soft HEAD~1 # 只撤销最近一次「未推送」的提交，改动留在工作区
git restore <file>      # 丢弃某个文件的未提交改动
```

**避免** `git reset --hard` + `git push -f`，除非确认没有其他人基于该分支工作。

误删了数据文件（`data/`、`exports/`）**不能用 git 恢复**——它们被 `.gitignore` 排除，只能从备份还原。

---

## 7. 安全红线

- 永不提交 `config.json`、`data/`、`logs/`、`exports/`（已在 `.gitignore`）
- 每次 `git add -A` 之前用 `git status --short` 扫一眼
- 万一 Key 被提交：**立刻到服务商后台吊销并重新生成**，再清理历史（`git filter-repo`），最后强推并通知协作者
- 截图外发前检查是否带出 Key 或个人路径

---

## 8. Issue 与 PR 维护

建议补两个模板（暂未提供）：

- `.github/ISSUE_TEMPLATE/bug_report.md`：系统版本、Python 版本、复现步骤、`logs/error.log` 片段
- `.github/pull_request_template.md`：改动说明 + 本地自测方式

处理节奏建议：

- 新 Issue 48 小时内给一次回应（哪怕只是「收到，我看看」）
- 无法复现的，请求补充 `logs/error.log` 与版本信息
- 合并 PR 前确认 CI 绿

---

## 9. 常见故障速查

| 现象 | 处理 |
| --- | --- |
| `RPC failed; connection reset` | `git config http.version HTTP/1.1`，重试 |
| `tag already exists` | 换版本号；或 `git tag -d v0.1.0` + `git push origin :refs/tags/v0.1.0`（仅限未发布） |
| 忘记先拉取，推送被拒 | `git pull --rebase` 后重推 |
| 每次只改文档也触发完整 CI | 在 workflow 加 `paths-ignore: ['docs/**', '*.md']` |
| 服务没生效 | 后端改动需重启进程；前端刷新即可 |

---

## 10. 数据备份

升级或大改之前：

```powershell
Copy-Item data\app.db "data\app-$(Get-Date -Format yyyyMMdd).bak"
```

数据库是单文件 SQLite，复制即备份；`config.json` 单独保存（含 API Key，不要放进仓库）。
