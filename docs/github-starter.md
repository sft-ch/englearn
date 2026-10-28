# GitHub 社区入门手册

> 面向零基础读者：从注册账号、装好 Git，到维护自己的仓库、上传内容，再到给别人的项目提第一个 Pull Request。
> 全程以命令行 + GitHub 网页端为主，Windows 环境为例（macOS / Linux 把路径换成你自己的即可）。
> 文中示例仓库用 `sft-ch/englearn`（本仓库），你可以换成自己的名字跟着做。

---

## 目录

- [第 0 章 先搞清楚这些词（5 分钟）](#第-0-章-先搞清楚这些词5-分钟)
- [第 1 章 注册账号与配置个人资料](#第-1-章-注册账号与配置个人资料)
- [第 2 章 安装 Git 并做一次基础配置](#第-2-章-安装-git-并做一次基础配置)
- [第 3 章 让 GitHub 认识你：两种认证方式](#第-3-章-让-github-认识你两种认证方式)
- [第 4 章 拿到一个仓库：克隆与新建](#第-4-章-拿到一个仓库克隆与新建)
- [第 5 章 仓库的"门面"：README、目录结构、License](#第-5-章-仓库的门面readme目录结构license)
- [第 6 章 日常循环：改 → 提交 → 推送](#第-6-章-日常循环改--提交--推送)
- [第 7 章 分支与冲突处理](#第-7-章-分支与冲突处理)
- [第 8 章 把内容上传到仓库](#第-8-章-把内容上传到仓库)
- [第 9 章 参与别人的项目：Fork 与 Pull Request](#第-9-章-参与别人的项目fork-与-pull-request)
- [第 10 章 Issue：提问与任务跟踪](#第-10-章-issue提问与任务跟踪)
- [第 11 章 社区规范与礼仪](#第-11-章-社区规范与礼仪)
- [第 12 章 常见报错对照表](#第-12-章-常见报错对照表)
- [第 13 章 安全、备份与"别做的事"](#第-13-章-安全备份与别做的事)
- [第 14 章 练习清单与后续学习](#第-14-章-练习清单与后续学习)
- [附录 A 命令速查卡](#附录-a-命令速查卡)
- [附录 B 术语表](#附录-b-术语表)

---

## 第 0 章 先搞清楚这些词（5 分钟）

新手最容易卡住的不是命令，而是名词。先花五分钟认人：

| 名词 | 一句话解释 |
|---|---|
| **Git** | 装在你电脑上的**版本管理工具**，负责记录"每次改了什么"。断网也能用。 |
| **GitHub** | 一个网站，把 Git 仓库托管在云端，顺便提供协作功能（Issue、PR、CI）。 |
| **仓库（repository / repo）** | 一个被 Git 管理的文件夹，包含文件 + 完整修改历史。可以理解成"带时间机器的项目文件夹"。 |
| **提交（commit）** | 一次存档。每一次提交都有编号（如 `88ff37a`）和说明，随时可以回到某个存档点。 |
| **分支（branch）** | 从主线分出来的一条平行时间线，用来做实验/开发新功能，不影响主线。 |
| **远程（remote）** | 云端那份仓库。你本地这份叫"本地仓库"，默认远程名叫 `origin`。 |
| **克隆（clone）** | 把远程仓库整个下载到本地（含历史），得到一份可改可提交的副本。 |
| **推送（push）/ 拉取（pull）** | push = 把本地提交传到云端；pull = 把云端的新提交取回本地。 |
| **Issue（议题）** | 仓库里的"任务单 / 问题单 / 讨论帖"。提 bug、提需求、记待办都用它。 |
| **Fork（派生）** | 把**别人**的仓库复制一份到自己账号下。你没有权限直接改别人的仓库，所以先 Fork。 |
| **Pull Request（PR，拉取请求）** | "我把改动做好了，请你合并进你的仓库"。代码评审、讨论、CI 检查都在 PR 里进行。 |
| **Star（星标）** | 收藏 / 点赞，纯个人标记，不影响仓库。 |
| **Watch（关注）** | 订阅这个仓库的动态通知（新 Issue、新 PR）。不想被消息淹没就别乱 Watch。 |

一句话记住分工：**Git 管本地历史，GitHub 管云端和协作。**

**动手练习 0**：打开 <https://github.com/sft-ch/englearn>，在页面上把上面 5 个词找出来——仓库名在哪、Star 按钮在哪、Issues 标签页在哪、Commits 列表在哪。

---

## 第 1 章 注册账号与配置个人资料

### 1.1 注册

1. 打开 <https://github.com>，点右上角 **Sign up**。
2. 依次填：邮箱 → 密码 → 用户名 → 邮箱验证码 → 完成人机验证。
3. 去邮箱点验证链接（**不验证很多功能用不了**）。

**用户名（username）就是你的永久门牌号**，会出现在 `github.com/你的名字` 和所有仓库地址里：

- 只能用英文字母、数字、连字符 `-`；
- 不能以 `-` 开头或结尾，不能有连续 `--`；
- 最长 39 字符；
- **可以改**（Settings → Account），但改完后旧仓库地址会跳转、你本地的 remote 地址需要自己更新。

建议：用真名拼音缩写 + 行业词，或一个你长期不会腻的 ID。别用纯数字（难记）和带年份的（会过期感）。

### 1.2 必做的三项设置

进入右上角头像 → **Settings**：

**① 开启双重验证（2FA）** — Settings → Password and authentication → Two-factor authentication。
GitHub 现在对贡献者强制 2FA。用手机 App（Microsoft Authenticator / 1Password 等）扫码，**务必把恢复码（recovery codes）抄下来存好**，手机丢了靠它救号。

**② 确认邮箱隐私** — Settings → Emails。
建议勾选 **Keep my email addresses private**，GitHub 会给你一个 `xxxx@users.noreply.github.com` 地址；提交代码时用它，真实邮箱就不会出现在公开的提交记录里。

**③ 完善个人主页** — Settings → Public profile：头像、姓名、简介、所在地、个人网站。
另外，新建一个**和用户名同名的仓库**（如 `sft-ch/sft-ch`），在里面放 `README.md`，内容会显示在你主页最上方。这是 GitHub 的"个人名片"，成本极低、效果很好。

### 1.3 免费的额度够不够

个人免费计划：公开/私有仓库数量不限、协作者不限、GitHub Actions 每月 2000 分钟（私有仓库）、GitHub Pages 静态托管免费。**入门阶段完全够用，不需要付费。**

**动手练习 1**：开启 2FA 并保存恢复码；上传头像；把邮箱设为私有。

---

## 第 2 章 安装 Git 并做一次基础配置

### 2.1 安装

Windows 两种方式选一种：

```powershell
# 方式一：winget（Windows 10/11 自带）
winget install --id Git.Git -e --source winget

# 方式二：去 https://git-scm.com/download/win 下载安装包，一路下一步
```

装完**关掉再重开**终端，验证：

```powershell
git --version
# 期望输出类似：git version 2.47.0.windows.1
```

macOS：`brew install git` 或 `xcode-select --install`。Linux：`sudo apt install git`。

### 2.2 一次性配置（每台电脑只做一次）

Git 需要知道"这次提交是谁做的"，否则不让提交：

```powershell
# 身份（必填）——邮箱建议用 1.2 里的 noreply 地址
git config --global user.name  "你的名字或昵称"
git config --global user.email "12345678+sft-ch@users.noreply.github.com"

# 默认分支名用 main（GitHub 现在的默认，别再叫 master 了）
git config --global init.defaultBranch main

# Windows 换行符处理：仓库里存 LF，检出到本地转 CRLF
git config --global core.autocrlf true

# 中文文件名不要显示成 \346\226\207 这种转义
git config --global core.quotepath false

# 让 git 输出彩色、分页更好读
git config --global color.ui auto

# 看一眼全部配置
git config --list
```

解释两个容易踩的点：

- **`core.autocrlf true`**：Windows 用 CRLF 换行，Linux/macOS 用 LF。不设这个，每次拉取都会提示 "LF will be replaced by CRLF"，或者整个文件显示被改过但其实只差换行符。
- **`core.quotepath false`**：不设它，中文文件名在 `git status` 里会显示成一串八进制转义，根本认不出是哪个文件。

### 2.3 顺手装个 GitHub CLI（可选但强烈推荐）

`gh` 是官方命令行工具，能代替大部分网页操作（建仓库、开 PR、看 CI 日志）：

```powershell
winget install --id GitHub.cli -e --source winget
gh --version
```

后文遇到能用 `gh` 简化的地方会标出来，**不装也不影响**，用网页一样能做。

**动手练习 2**：装好 Git，跑通 `git --version` 和 `git config --list`，确认 `user.name`、`user.email` 是你自己的。

---

## 第 3 章 让 GitHub 认识你：两种认证方式

GitHub 从 2021 年起**不再接受账号密码**做 git 操作。你有两条路：

### 方案 A：SSH 密钥（推荐，一次配置长期有效）

原理：你本地有一对钥匙，公钥交给 GitHub，私钥留自己手里；每次连接自动验证。

```powershell
# 1) 生成密钥（一路回车，密码短语可留空）
ssh-keygen -t ed25519 -C "你的邮箱"

# 2) 把公钥复制到剪贴板（注意是 .pub 结尾的那个）
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard

# 3) 粘贴到 GitHub：Settings → SSH and GPG keys → New SSH key
#    Title 随便写（如 "我的笔记本"），Key 粘贴，点 Add SSH key

# 4) 测试
ssh -T git@github.com
# 首次会问 "Are you sure you want to continue connecting?"，输 yes
# 成功输出：Hi sft-ch! You've successfully authenticated...
```

⚠️ `id_ed25519`（无后缀）是**私钥，绝对不能给任何人、不能提交到仓库**。只上传 `.pub`。

### 方案 B：HTTPS + 个人访问令牌（PAT）

不想配 SSH 就用这个，但每次推送要提供令牌。

1. 头像 → Settings → Developer settings → **Personal access tokens** → Tokens (classic) → Generate new token。
2. 勾选 `repo` 权限（要操作 Actions/工作流再加 `workflow`），设置过期时间（建议 90 天）。
3. 生成后**立刻复制**（只显示一次），存到密码管理器。
4. 推送时用户名填 GitHub 用户名，密码栏粘贴这个令牌。Windows 会把它存进"凭据管理器"，之后不再问。

### 方案 C：`gh auth login`（最省事）

```powershell
gh auth login
# 选 GitHub.com → HTTPS → 用浏览器登录（会给你一个 8 位设备码，在网页里输入）
gh auth status   # 确认已登录及权限
```

它同时帮你配置好 git 的凭据，`gh auth setup-git` 可显式写入。

> 如果你要在仓库里改 GitHub Actions 工作流文件（`.github/workflows/*.yml`），令牌必须有 `workflow` 权限，否则推送会被拒绝。补权限：`gh auth refresh -h github.com -s workflow`。

**动手练习 3**：用方案 A 或 C 配置好认证，跑 `ssh -T git@github.com` 或 `gh auth status` 看到成功。

---

## 第 4 章 拿到一个仓库：克隆与新建

### 4.1 克隆已存在的仓库

在 GitHub 仓库页面点绿色 **Code** 按钮，能看到两个地址。SSH 地址长这样：

```powershell
cd D:\projects
git clone git@github.com:sft-ch/englearn.git
cd englearn
```

克隆完成后你有了：完整文件 + 全部提交历史 + 一个叫 `origin` 的远程指向该仓库。

```powershell
git remote -v      # 看远程地址
git log --oneline -5   # 看最近 5 条提交
```

### 4.2 新建自己的仓库

**推荐：先在网页建空仓库，再克隆下来**（会自动带 README、License、.gitignore，省事）。

1. 右上角 **+** → **New repository**。
2. 填 Repository name（英文/短横线，如 `my-notes`）、Description（一句话说明）。
3. 选 Public（公开）或 Private（私有）。
4. **勾选** Add a README file、Add .gitignore（选 Python / Node 等）、Choose a license（后面 5.3 讲怎么选）。
5. Create repository，然后按页面提示克隆。

**另一种：本地已有文件夹，想推上去**

```powershell
cd D:\projects\my-notes
git init                                   # 把当前文件夹变成 Git 仓库
git add -A                                 # 暂存所有文件
git commit -m "chore: 初始化项目"           # 第一次存档
git branch -M main                         # 确认主分支叫 main
git remote add origin git@github.com:你的用户名/my-notes.git
git push -u origin main                    # -u 记住对应关系，以后直接 git push
```

> `git add -A` 之前一定先有 `.gitignore`（见 5.4），否则会把临时文件、虚拟环境、密钥一起提交上去。

**动手练习 4**：克隆 `englearn` 到本地，用 `git log --oneline` 数一下它有多少次提交。

---

## 第 5 章 仓库的"门面"：README、目录结构、License

别人（以及三个月后的你）判断一个仓库值不值得看，只看三样东西。

### 5.1 README.md —— 最重要的文件

它是仓库主页自动显示的内容。够用的 README 结构：

````markdown
# 项目名

一句话说明这是什么、解决什么问题。

![截图](docs/images/screenshot.png)

## 功能
- 功能一
- 功能二

## 快速开始
```bash
git clone git@github.com:你的用户名/项目名.git
cd 项目名
python app.py
```

## 文档
- [使用教程](docs/tutorial.md)
- [部署说明](docs/DEPLOY.md)

## 许可证
MIT
````

要点：**开头三行讲清是什么**、给一张截图、给能直接复制的运行命令、文档链接放前面。不要写一大段背景故事。

### 5.2 目录结构

```
项目名/
├── README.md          # 门面
├── LICENSE            # 许可证，必须有
├── .gitignore         # 哪些文件不进仓库
├── CHANGELOG.md       # 版本变更记录
├── docs/              # 文档、截图
├── src/ 或 core/      # 源码
├── tests/ 或 scripts/ # 测试与脚本
└── .github/
    ├── workflows/     # CI 配置
    └── ISSUE_TEMPLATE/# Issue 模板
```

原则：**目录名用小写英文**，文件名避免空格（用 `-` 或 `_`）。中文文件名在部分工具和链接里会出问题。

### 5.3 License —— 别人能不能用你的代码

没有 License 的公开仓库，法律上等于"保留所有权利"，别人不敢用。常用四种：

| 许可证 | 特点 | 适合 |
|---|---|---|
| **MIT** | 最短最宽松，保留版权声明即可任意使用 | 绝大多数小工具、示例代码 |
| **Apache-2.0** | 宽松，额外含专利授权条款 | 企业环境、可能涉及专利的项目 |
| **GPL-3.0** | 传染性：衍生作品也必须开源 | 你希望衍生品保持开源 |
| **CC-BY-4.0** | 不是软件许可证，针对文档/文章 | 纯文档、教程仓库 |

在网页新建仓库时勾选即可自动生成；已有仓库可以 **Add file → Create new file**，文件名写 `LICENSE`，GitHub 会提示选择模板。

### 5.4 .gitignore —— 防止误提交

列出"不该进仓库"的东西：本地数据、日志、虚拟环境、密钥配置。

```gitignore
# Python
__pycache__/
*.pyc
.venv/

# 本地数据与日志
data/
logs/
exports/

# 配置（可能含密钥）
config/config.json
.env

# 系统文件
.DS_Store
Thumbs.db
```

**验证某个文件确实被忽略了**：

```powershell
git check-ignore -v config/config.json
# 输出匹配到的规则说明即表示已忽略；无输出说明没被忽略，要补规则
```

### 5.5 版本记录

`CHANGELOG.md` 按版本记录"改了什么"，格式不必复杂：

```markdown
## [0.2.0] - 2026-10-28
### 新增
- 生词本按单词 / 短语 / 短句分类

### 修复
- 分类筛选「全部」计数显示为 0
```

**动手练习 5**：给你的仓库补一个 `LICENSE`、一个 `.gitignore`，并用 `git check-ignore` 验证敏感文件确实被排除。

---

## 第 6 章 日常循环：改 → 提交 → 推送

这是你 90% 的时间会用到的四条命令，记住循环就行：

```powershell
# ① 改文件（编辑器随便用）

# ② 看现在什么状态
git status            # 哪些文件被改/新增/删除
git diff              # 具体改了哪几行（q 退出）

# ③ 暂存 + 提交
git add README.md              # 暂存指定文件
git add -A                     # 或者暂存全部改动
git commit -m "docs: 补充快速开始说明"

# ④ 推到云端
git push
```

### 6.1 提交信息怎么写

格式：`类型(范围): 简短描述`，中文没问题。

| 类型 | 用于 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 只改文档 |
| `refactor` | 重构，行为不变 |
| `test` | 测试相关 |
| `chore` | 构建、依赖、杂项 |

好的例子：

```
feat(words): 生词本支持按类别筛选
fix(popup): 悬浮窗在双屏下位置偏移
docs(readme): 补充 Docker 部署说明
```

不好的例子：`update`、`修改`、`fix bug`、`asdf`。半年后你自己也看不懂。

**粒度原则：一次提交只做一件事。** 同时改了三个功能就提交三次，将来出问题好回滚。

### 6.2 拉取别人的改动

多人协作时，推送前先同步：

```powershell
git pull          # = fetch（下载）+ merge（合并到当前分支）
```

如果只有你一个人改，这一步经常可以省略，但**养成先 pull 再 push 的习惯**，能避免大部分"推送被拒绝"。

### 6.3 撤销的三种常见需求

```powershell
# 改动还没提交，想全部丢弃（危险：本地改动会没）
git restore .

# 已经 add 了，想撤出暂存区（文件内容不变）
git restore --staged 文件名

# 最新一条提交写错了说明，想改（未推送时）
git commit --amend -m "新的说明"
```

⚠️ 已经推送的提交不要用 `--amend` 再强推（`push -f`），会改掉别人的历史。已推送的想撤销，用 `git revert <提交号>` 生成一条反向提交。

**动手练习 6**：改一下你仓库的 README，走完 `status → diff → add → commit → push` 全流程，然后在 GitHub 网页上看到这次提交。

---

## 第 7 章 分支与冲突处理

### 7.1 分支：为什么需要

主分支（`main`）应该**随时可用**。新功能、实验性改动放在分支上做，做完了再合并。这样即使做砸了，主线也不受影响。

```powershell
git switch -c feat/vocab-tags   # 创建并切换到新分支（-c = create）
git branch                       # 看所有本地分支，* 是当前所在
git switch main                  # 切回主线
git merge feat/vocab-tags        # 把分支合并进当前分支（main）
git branch -d feat/vocab-tags    # 合并后删掉分支
git push -u origin feat/vocab-tags  # 把分支推到云端（用于开 PR）
```

> 老教程里的 `git checkout -b` 等价于 `git switch -c`，新版用 `switch` 更直观。

### 7.2 冲突是怎么产生的

两个人（或你自己两个分支）改了**同一个文件的同一区域**，Git 不知道听谁的，就会停下来让你决定。合并时你会看到：

```
Auto-merging README.md
CONFLICT (content): Merge conflict in README.md
Automatic merge failed; fix conflicts and then commit the result.
```

打开冲突文件，会看到：

```
<<<<<<< HEAD
当前分支的版本
=======
要合并进来的版本
>>>>>>> feat/vocab-tags
```

### 7.3 解决冲突三步

1. **编辑文件**：删掉 `<<<<<<<`、`=======`、`>>>>>>>` 这三行标记，把内容改成你最终想要的样子（保留一边、保留另一边，或两边融合）。
2. **标记已解决**：`git add README.md`
3. **完成合并**：`git commit`（Git 会预填一条合并提交信息，直接保存即可）

然后 `git push`。

**搞砸了想放弃？**

```powershell
git merge --abort      # 合并进行到一半，回到合并前的状态
git status             # 随时确认自己在什么状态
```

减少冲突的实用建议：

- 分支**活得短**：一天内能合就合，别开一个月的分支；
- 提交前先 `git pull`；
- 多人改同一个大文件的不同位置仍可能冲突，**大文件尽量拆分**；
- 格式化/改缩进/改行尾这类"全文件改动"单独提交，别和逻辑改动混在一起。

**动手练习 7**：在你的仓库开一个 `test/branch-demo` 分支，改一行 README，合并回 main，观察提交历史里出现分支合并的痕迹。

---

## 第 8 章 把内容上传到仓库

三种方式，按场景选：

### 8.1 网页直接上传（改一两个文件最快）

仓库页面 → **Add file** → **Upload files** → 拖入文件 → 底下写提交说明 → Commit changes。

- 单文件网页上限 25 MB；超过要用命令行或 Git LFS。
- 适合传图片、文档、改错别字。
- 缺点：不适合批量改动，也没有本地预览。

### 8.2 命令行提交（推荐，批量改动用这个）

```powershell
# 假设你要把 exports/ 里的文档放进仓库的 docs/
Copy-Item exports\教程.pdf docs\ -Force
git add docs/教程.pdf
git commit -m "docs: 添加使用教程 PDF"
git push
```

### 8.3 大文件：不要直接提交

Git 会保存每个文件的每个版本，**一个 80 MB 的视频提交几次，仓库就膨胀几百 MB，而且删掉也永久留在历史里**。

- GitHub 硬上限：单文件 **100 MB**，超过直接拒收；
- 仓库建议控制在 1 GB 以内；
- 确实需要版本管理大文件 → 用 **Git LFS**（`git lfs track "*.psd"`），但在 LFS 有免费额度限制；
- 更常见的做法：**大文件放 Releases 附件或网盘**，仓库里只放链接。

### 8.4 误提交了怎么办

```powershell
# 还没推送：撤销这次提交，文件保留在本地
git reset --soft HEAD~1
git restore --staged 大文件.zip
# 补进 .gitignore 后再正常提交

# 已经推送：从仓库移除，但历史里还在（敏感信息必须换密钥！）
git rm --cached 大文件.zip
git commit -m "chore: 移除误提交的大文件"
git push
```

⚠️ **误提交了密钥/密码**：删文件没用，历史里能翻出来。正确做法是 **立刻去服务商后台吊销并重新生成密钥**（比如换掉 API Key），然后才考虑清理历史（`git filter-repo` 属于进阶操作，见第 14 章的学习路径）。

**动手练习 8**：在仓库里新建 `docs/notes.md`，用命令行提交并推送；再用网页的 Add file 改一个字，体验两种方式的差别。

---

## 第 9 章 参与别人的项目：Fork 与 Pull Request

场景：你想给别人的项目修个 bug 或补个文档。你没有该仓库的写权限，所以流程是 **Fork → 改 → PR**。

### 9.1 完整链路（六步）

**① Fork**：打开目标仓库页面，点右上角 **Fork** → **Create fork**。
你的账号下多了一个副本：`你的用户名/目标仓库`。

**② 克隆你自己那份**：

```powershell
git clone git@github.com:你的用户名/目标仓库.git
cd 目标仓库
```

**③ 关联上游（原仓库）**，方便以后同步：

```powershell
git remote add upstream git@github.com:原作者/目标仓库.git
git remote -v      # 应该看到 origin（你的）和 upstream（原作者的）
```

**④ 开分支改代码**（**不要直接在 main 上改**）：

```powershell
git switch -c fix/typo-in-readme
# 改文件…
git add -A
git commit -m "docs: 修正 README 中的拼写错误"
git push -u origin fix/typo-in-readme
```

**⑤ 开 PR**：推送后 GitHub 会在仓库页顶部显示黄色提示条 → **Compare & pull request**。
也可以去原仓库页面 → **Pull requests** → **New pull request** → **compare across forks** → 选你的分支。

PR 里写清楚三件事：

```markdown
## 这个 PR 做了什么
修正 README 第 12 行的拼写错误。

## 为什么
拼写错误会让读者误解配置项名称。

## 怎么验证
本地打开 README 渲染后确认无误。

Closes #12
```

> 最后一行 `Closes #12` 表示合并后自动关闭第 12 号 Issue，很实用。

**⑥ 等评审、改、合并**：维护者可能提修改意见。你只需在**同一个分支**上继续提交并 push，PR 会自动更新，不需要重新开 PR。

### 9.2 保持你的 Fork 同步

原仓库一直在更新，你的 Fork 会落后：

```powershell
git switch main
git fetch upstream
git merge upstream/main
git push origin main
```

或用 `gh` 一条命令：`gh repo sync 你的用户名/目标仓库`。

> 网页上也能点 **Sync fork → Update branch**，最省事。

### 9.3 社区礼仪（很重要）

- **先看有没有人提过**：搜索 Issues 和 PR，重复提问会消耗维护者耐心。
- **小改动别开大 PR**：修个错别字不需要顺手重构三个文件。
- **一个 PR 只做一件事**，方便评审和回滚。
- **不要给无关的人 @ 提醒**，也不要催问"什么时候合并"（维护者多是业余时间做）。
- 被拒绝了别气馁，问清楚原因；维护者也是人，礼貌讨论通常有转机。

**动手练习 9**：Fork `sft-ch/englearn`，在你自己的副本里改一行 README，开一个 PR（可以只给自己看，练习完整流程后关闭）。

---

## 第 10 章 Issue：提问与任务跟踪

Issue 是仓库的"任务本 + 论坛"。它有两种典型用法：

### 10.1 提一个好的 Bug Issue

标题格式：`[模块] 现象`，例如 `[悬浮窗] 双屏下弹窗出现在错误屏幕`。

正文包含四块：

```markdown
## 复现步骤
1. 打开 http://127.0.0.1:8765
2. 在第二块屏幕上选中一段英文
3. 观察悬浮窗位置

## 期望结果
悬浮窗出现在鼠标旁边

## 实际结果
悬浮窗出现在主屏左下角

## 环境
- Windows 11 23H2
- Python 3.12.4
- Englearn v0.1.0
- 双屏：1920×1080 + 2560×1440

（附截图）
```

**要点**：能复现、有环境信息、有截图。只说"用不了"的 Issue 基本无法处理。

### 10.2 提功能需求

说清 **你要解决什么问题**，而不是"你给我加个按钮"。维护者更愿意接受"我每次都要手动翻到日历才能复习，希望能一键跳到今天"这种带场景的描述。

### 10.3 维护别人的 Issue 时

- **标签（Labels）** 分类：`bug`、`enhancement`、`question`、`documentation`、`good first issue`、`help wanted`。
- **指派（Assignees）**：谁来干。
- **里程碑（Milestones）**：归到哪个版本。
- **Projects**：看板视图，做任务管理。
- 关闭时说明原因（"已在 #45 修复"），比默默关掉友好得多。

### 10.4 你自己的仓库怎么管

小项目最简单的用法：**想到什么先开 Issue 记下来**，做完再关。这样不会忘，也留下了"为什么做这个改动"的记录。

**动手练习 10**：在你自己的仓库提一个 Issue，用上面的模板写，给自己打上 `bug` 标签，然后关闭它。

---

## 第 11 章 社区规范与礼仪

一个仓库除了代码，还常带三个"社交文件"：

| 文件 | 作用 |
|---|---|
| `README.md` | 这是什么、怎么用 |
| `CONTRIBUTING.md` | 想贡献的人该怎么做（分支规范、提交格式、跑测试的方法） |
| `CODE_OF_CONDUCT.md` | 行为准则，约定不可接受的行为及处理方式 |

`CONTRIBUTING.md` 最小可用版：

```markdown
# 如何贡献

## 提 Issue
- 先搜索是否已有相同问题
- Bug 请附复现步骤与环境信息

## 提 Pull Request
1. Fork 并新建分支：`git switch -c feat/你的功能`
2. 提交信息遵循 `类型(范围): 描述`
3. 提交前本地跑通测试：`python scripts/selftest.py`
4. 一个 PR 只做一件事

## 代码风格
- Python 遵循 PEP 8
- 中文注释可以，但变量名用英文
```

GitHub 会在新建 Issue / PR 时自动提示阅读这些文件。

**通用礼仪三条**：

1. **先搜索，再提问**——90% 的问题已经有人问过。
2. **提供可复现的信息**——"报错了"不是信息，"这段命令 + 这个报错 + 这个环境"才是。
3. **对事不对人**——指出问题可以，嘲讽不行。

**动手练习 11**：给仓库加一个 `CONTRIBUTING.md`，写上你自己能接受的贡献流程（哪怕只有三条）。

---

## 第 12 章 常见报错对照表

| 报错 / 现象 | 原因 | 解决 |
|---|---|---|
| `fatal: not a git repository` | 当前目录不是仓库 | `cd` 进仓库目录，或 `git init` |
| `Permission denied (publickey)` | SSH 密钥没配好 | `ssh -T git@github.com` 测试；确认公钥已加到 GitHub；`ssh-add ~/.ssh/id_ed25519` |
| `Authentication failed` / 提示输密码 | 已不支持账号密码 | 改用 PAT 或 SSH（第 3 章） |
| `Updates were rejected because the remote contains work` | 云端比你新 | `git pull --rebase` 再 `git push` |
| `refusing to allow an OAuth App to create or update workflow` | 令牌缺 `workflow` 权限 | `gh auth refresh -h github.com -s workflow` |
| `LF will be replaced by CRLF` | 换行符差异（警告，非错误） | 已设 `core.autocrlf true` 可忽略；或加 `.gitattributes` 固定 |
| 中文文件名显示成 `\346\226\207` | 未关闭路径转义 | `git config --global core.quotepath false` |
| `File ... is 105.00 MB; this exceeds GitHub's file size limit` | 超 100 MB | 移出仓库改用 Releases，或用 Git LFS |
| `error: Your local changes would be overwritten by merge` | 本地有未提交改动 | `git stash` → 操作 → `git stash pop` |
| `You are in 'detached HEAD' state` | 直接切到了某个提交而非分支 | `git switch main` 回到分支；要保留改动就 `git switch -c 新分支` |
| 终端中文乱码（Windows） | 编码不一致 | `chcp 65001`，或设 `$env:PYTHONUTF8=1` |
| `push` 卡住 / `Connection was reset` | 网络或 HTTP 版本问题 | 先试 `git config http.version HTTP/2`；或用 SSH 代替 HTTPS |
| 提交作者显示成别人的名字 | 全局 `user.name/email` 配错 | 重新 `git config --global user.email ...`，旧提交需改写历史（进阶） |

**通用排查法**：先看 `git status`，再看 `git log --oneline -5`，最后看 `git remote -v`。这三个命令能定位 80% 的问题。

---

## 第 13 章 安全、备份与"别做的事"

### 13.1 绝对不能提交的东西

- API Key、token、密码、数据库连接串
- 私钥文件（`id_rsa`、`id_ed25519`、`.pem`）
- 含个人信息的真实数据（客户名单、成绩、身份证号）
- 公司内部代码（未经许可）

**做法**：新建仓库**第一件事**是写 `.gitignore`，把 `config/`、`data/`、`.env`、`*.key` 都列进去，然后 `git status` 确认没有敏感文件再 `git add`。

**已经提交了怎么办**：立刻去服务商处**吊销并换新密钥**（这是唯一真正有效的补救），然后清理文件。只 `git rm` 而不换密钥等于没处理。

### 13.2 备份

- GitHub 上的仓库**不是备份**：账号被盗、误删、封禁都可能丢。
- 定期做一份完整镜像：

```powershell
git clone --mirror git@github.com:你的用户名/仓库.git D:\backup\仓库.git
```

- 重要版本打 **tag** 并发 **Release**，别人下载的是稳定版，你也有快照。

### 13.3 危险操作清单（执行前先确认）

| 命令 | 后果 |
|---|---|
| `git reset --hard` | 丢弃所有未提交改动，不可恢复 |
| `git push -f` | 覆盖云端历史，可能删掉别人的提交 |
| `git clean -fdx` | 删除所有未跟踪文件（含你的数据） |
| 删除仓库（网页 Danger Zone） | 整仓消失，需手输仓库名确认，且**无法找回** |
| `git branch -D` | 强制删分支，未合并的提交可能丢失 |

原则：**先 `git status`、先备份、先确认目标路径**，再执行不可逆操作。

### 13.4 账号安全

- 开 2FA，恢复码离线保存。
- 令牌设过期时间，权限最小化（只给需要的 scope）。
- 定期检查 Settings → Sessions 里的登录设备，踢掉不认识的。
- 别人发来的"帮我点个链接授权"一律先用官方域名核对。

---

## 第 14 章 练习清单与后续学习

### 14.1 入门验收清单

按顺序做，全打勾说明你已经能独立维护仓库了：

- [ ] 注册账号、开 2FA、邮箱设为私有
- [ ] 安装 Git，配置 `user.name` / `user.email` / `core.autocrlf`
- [ ] 配好 SSH 或 `gh auth login`，验证通过
- [ ] 新建一个公开仓库，带 README + .gitignore + LICENSE
- [ ] 克隆到本地，改 README，走完 `add → commit → push`
- [ ] 开一个分支，改点东西，合并回 main
- [ ] 故意制造一次冲突并手动解决
- [ ] 用 `git check-ignore` 验证敏感文件被忽略
- [ ] Fork 一个仓库，开一个 PR（自测后关闭也行）
- [ ] 给自己的仓库提一个 Issue 并关闭
- [ ] 补一个 `CONTRIBUTING.md`
- [ ] 打一个 tag，发一个 Release

### 14.2 后续学习路径（按顺序，别跳）

1. **Markdown 语法** —— README 写得好不好，一半看排版。
2. **`.gitattributes`** —— 跨平台换行符、二进制文件处理。
3. **GitHub Actions** —— 提交后自动跑测试、自动构建（`.github/workflows/*.yml`）。
4. **GitHub Releases** —— 给版本附二进制包、写发布说明。
5. **GitHub Pages** —— 把 `docs/` 变成一个网站。
6. **`git rebase` / `git bisect`** —— 整理提交历史、定位哪次提交引入了 bug。
7. **`git filter-repo`** —— 清理历史中的大文件或泄露的密钥（高风险，操作前先镜像备份）。

### 14.3 把流程套到本项目（englearn）上

| 你要做的事 | 命令 |
|---|---|
| 改了 `core/` 或 `app.py` | 提交后要**重启服务**才生效 |
| 只改了 `web/` 前端 | 浏览器 **Ctrl+F5** 刷新即可 |
| 验证没改坏 | `python scripts/selftest.py`（期望 15/15 通过） |
| 推上去看 CI | `gh run list --limit 5` → `gh run watch <id>` |
| 看失败日志 | `gh run view <id> --log-failed` |
| 发下一个版本 | 改 `VERSION`、更新 CHANGELOG、`git tag`、`gh release create` |

更细的版本发布与 CI 流程见 [MAINTAINING.md](MAINTAINING.md)。

---

## 附录 A 命令速查卡

```powershell
# —— 配置（一次）——
git config --global user.name "名字"
git config --global user.email "邮箱"
git config --global init.defaultBranch main
git config --global core.autocrlf true
git config --global core.quotepath false
git config --list

# —— 获取仓库 ——
git clone git@github.com:用户/仓库.git
git init
git remote add origin git@github.com:用户/仓库.git
git remote -v

# —— 日常循环 ——
git status
git diff
git add 文件名          # 单个
git add -A              # 全部
git commit -m "feat(scope): 说明"
git push
git pull

# —— 历史 ——
git log --oneline -10
git log --graph --oneline --all
git show <提交号>
git diff HEAD~1

# —— 分支 ——
git branch
git switch -c feat/xxx
git switch main
git merge feat/xxx
git branch -d feat/xxx

# —— 撤销 ——
git restore .                       # 丢弃未提交改动
git restore --staged 文件名          # 撤出暂存区
git commit --amend -m "新说明"       # 改最后一条提交（未推送）
git revert <提交号>                  # 生成反向提交（已推送时用这个）

# —— 同步 Fork ——
git fetch upstream
git merge upstream/main
git push origin main

# —— GitHub CLI ——
gh auth login
gh auth status
gh repo create
gh pr create --fill
gh pr merge --squash --delete-branch
gh issue list
gh run list --limit 5
gh run view <id> --log-failed
gh release create v0.2.0 --notes-file notes.md
```

## 附录 B 术语表

| 术语 | 解释 |
|---|---|
| 工作区 / 暂存区 / 仓库 | 改的文件（工作区）→ `git add` 后进暂存区 → `git commit` 后进仓库历史 |
| HEAD | 当前所在位置的指针，通常指向某个分支的最新提交 |
| origin / upstream | 远程仓库的约定名：`origin` 是你自己的那份，`upstream` 是被 Fork 的原仓库 |
| tag | 给某个提交起的固定名字，常用于标记版本号（`v0.1.0`） |
| HEAD detached | 当前不在任何分支上，而是直接停在某个提交处，此时提交容易丢 |
| merge / rebase | 都是合并：merge 保留分叉历史，rebase 把提交"搬"到目标分支后面，历史更线性但会改写提交号 |
| squash | 把多条提交压成一条再合并，历史更干净 |
| stash | 临时把未提交的改动收起来，腾出干净的工作区 |
| CI（持续集成） | 每次提交后自动跑测试/构建，结果标在 PR 上 |
| LFS | Git Large File Storage，用指针代替大文件本体 |
| Release | 基于某个 tag 发布的正式版本，可附二进制文件和说明 |
