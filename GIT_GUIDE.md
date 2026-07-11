# Git & GitHub 操作指南 — 多视角切换管理器

> 适用项目: `c:\myobs\` | 远程仓库: GitHub | 分支策略: master + feature 分支

---

## 目录

1. [基本概念](#1-基本概念)
2. [首次推送（已完成本地初始化后）](#2-首次推送已完成本地初始化后)
3. [日常开发流程](#3-日常开发流程)
4. [分支操作](#4-分支操作)
5. [常用命令速查](#5-常用命令速查)
6. [常见问题](#6-常见问题)

---

## 1. 基本概念

### 1.1 Git 是什么？

Git 是一个**版本控制系统**，它会记录你每一次代码修改，就像一个"存档系统"：
- 每保存一次代码状态，叫做一次 **commit（提交）**
- 可以随时回到之前的任意一个 commit
- 可以开出 **分支（branch）** 做实验性修改，不影响主代码

### 1.2 GitHub 是什么？

GitHub 是一个**远程代码托管平台**，你可以把本地的 Git 仓库"推"到 GitHub 上：
- 代码备份在云端，不怕电脑坏
- 方便多个开发者协作
- 可以浏览提交历史、管理分支

### 1.3 关键术语

| 术语 | 解释 | 类比 |
|------|------|------|
| **仓库 (repo)** | 一个项目的 Git 管理区域 | 项目的"文件夹" |
| **提交 (commit)** | 一次代码快照 | 游戏"存档" |
| **分支 (branch)** | 独立的开发线 | RPG 游戏的"支线剧情" |
| **远程 (remote)** | GitHub 上的仓库 | 云端备份 |
| **推送 (push)** | 把本地 commit 上传到 GitHub | 把存档上传云端 |
| **拉取 (pull)** | 从 GitHub 下载最新代码 | 从云端下载存档 |
| **暂存 (stage)** | 选择哪些文件加入下次 commit | 选择哪些道具放入背包 |
| **合并 (merge)** | 把分支的修改并入主分支 | 把支线剧情合并回主线 |
| **main/master** | 默认主分支 | 主线剧情 |

### 1.4 三个区域

```
工作区 (Working)  ──git add──▶  暂存区 (Staging)  ──git commit──▶  本地仓库 (Local)
                                                                        │
                                                              git push  │  git pull
                                                                        ▼
                                                                 远程仓库 (GitHub)
```

---

## 2. 首次推送（已完成本地初始化后）

### 2.1 前提条件

确认本地 Git 已完成初始化和首次 commit：

```powershell
cd c:\myobs
git log --oneline    # 应该看到至少一条 commit
```

### 2.2 添加远程仓库并推送

```powershell
cd c:\myobs

# 步骤1: 添加远程仓库地址（替换为你的实际地址）
git remote add origin https://github.com/yelunz/multi-view-stream-switcher.git

# 步骤2: 推送本地 master 分支到 GitHub
git push -u origin master
```

> `-u` 参数会绑定本地 `master` 分支与远程 `origin/master`，之后只需 `git push` 即可。

### 2.3 验证

打开 https://github.com/yelunz/multi-view-stream-switcher 确认代码已上传。

---

## 3. 日常开发流程

每完成一个功能或修复一个 bug 后，执行以下流程：

### 3.1 标准流程（在主分支快速修复）

```powershell
cd c:\myobs

# 1. 查看当前有哪些修改
git status

# 2. 将修改添加到暂存区
git add .                              # 添加所有修改
# 或
git add manager_ui.pyw                # 只添加指定文件

# 3. 提交
git commit -m "fix: 修复了XXX问题"

# 4. 推送到 GitHub
git push
```

### 3.2 Commit 信息规范

使用 **type: 描述** 格式：

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 添加新桌面创建流程` |
| `fix:` | 修复 bug | `fix: 修复静音失败问题` |
| `refactor:` | 重构代码 | `refactor: 优化日志系统` |
| `docs:` | 文档更新 | `docs: 更新 Git 操作指南` |
| `chore:` | 杂项 | `chore: 更新 .gitignore` |

### 3.3 本次项目的日志规范

`manager_ui.pyw` 中已统一使用带前缀的日志格式：

```
[模块-步骤-状态] 描述信息
```

例如：
- `[新增桌面-步骤1-完成] 新桌面已创建`
- `[新增桌面-步骤2-失败] 启动浏览器时出错`

这样在 `debug.log` 或 UI 日志区域可以快速定位问题出在哪一步。

---

## 4. 分支操作

### 4.1 为什么用分支？

当你开发一个**大功能**时（比如"批量导入"），如果直接在 `master` 上改，可能改到一半代码就跑不起来了。分支让你在独立空间开发，完成后再合并。

### 4.2 创建功能分支

```powershell
# 1. 确保当前在 master，且代码是最新的
git checkout master
git pull

# 2. 创建并切换到新分支（分支名用英文，kebab-case）
git checkout -b feature/new-browser-flow

# 3. 在新分支上开发... 修改代码...

# 4. 提交修改
git add .
git commit -m "feat: 实现新桌面创建流程"

# 5. 推送到 GitHub（首次推送新分支需要 -u）
git push -u origin feature/new-browser-flow
```

### 4.3 合并分支到 master

```powershell
# 1. 切回 master
git checkout master
git pull                               # 拉取最新代码

# 2. 合并功能分支
git merge feature/new-browser-flow

# 3. 推送合并后的 master
git push

# 4. 删除已合并的本地分支（可选）
git branch -d feature/new-browser-flow

# 5. 删除远程分支（可选）
git push origin --delete feature/new-browser-flow
```

### 4.4 本项目推荐分支策略

```
master  ────●───────────●────────●────  (稳定版本)
              \         /        /
feature-A     ●──●──●──        /      (功能分支)
                               /
feature-B    ●──●──●──────────       (功能分支)
```

- `master`: 始终保持可运行的稳定版本
- `feature/xxx`: 每个新功能一个分支，开发完成后合并

---

## 5. 常用命令速查

### 5.1 查看状态

```powershell
git status              # 查看修改状态
git log --oneline -10   # 查看最近 10 条提交
git diff                # 查看未暂存的修改内容
git diff --staged       # 查看已暂存的修改内容
```

### 5.2 撤销操作

```powershell
# 撤销工作区修改（放弃所有改动，回到上次 commit 状态）
git checkout -- manager_ui.pyw

# 撤销暂存区的文件（从暂存区移除，保留工作区修改）
git reset HEAD manager_ui.pyw

# 撤销最近一次 commit（保留修改在工作区）
git reset --soft HEAD~1

# 彻底撤销最近一次 commit（丢弃修改）
git reset --hard HEAD~1
```

### 5.3 分支操作

```powershell
git branch                    # 查看本地分支列表
git branch -a                 # 查看所有分支（含远程）
git checkout master           # 切换到 master
git checkout -b feature/xxx   # 创建并切换新分支
git branch -d feature/xxx     # 删除本地分支
```

### 5.4 远程操作

```powershell
git push                           # 推送当前分支
git push -u origin master          # 首次推送并绑定
git pull                           # 拉取远程更新
git remote -v                      # 查看远程仓库地址
```

### 5.5 紧急情况

```powershell
# 暂存当前修改（不想 commit 但需要切换分支）
git stash
git stash pop                      # 恢复暂存的修改

# 查看某人改了什么
git log --author="yelunz" --oneline

# 回到某个历史版本（只读）
git checkout <commit-hash>
git checkout master                # 回到最新
```

---

## 6. 常见问题

### Q: `git push` 提示需要用户名密码？

A: GitHub 不再支持密码登录，需要使用 **Personal Access Token (PAT)**：

1. 打开 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 生成后复制 token
5. Push 时，用户名填你的 GitHub 用户名，密码填这个 token

如果是 Windows，建议安装 **GitHub CLI** 可以免去每次输入：

```powershell
winget install GitHub.cli
gh auth login    # 按提示在浏览器中授权
```

### Q: `git push` 报 `fatal: remote origin already exists`？

A: 远程地址已存在，先删除再添加：

```powershell
git remote remove origin
git remote add origin https://github.com/yelunz/multi-view-stream-switcher.git
```

### Q: 提交了不该提交的文件（如 config.json 含密码）？

A: 用 `.gitignore` 忽略并从 Git 追踪中移除：

```powershell
# 在 .gitignore 中添加文件
echo "config.json" >> .gitignore

# 从 Git 追踪中移除（但保留本地文件）
git rm --cached config.json
git add .gitignore
git commit -m "chore: 排除含密码的配置文件"
git push
```

> **注意**: 如果密码已经推送到 GitHub，请立即去 GitHub 更换密码！

### Q: 合并时出现冲突怎么办？

A: 当两个分支修改了同一文件同一位置时会发生冲突。Git 会在文件中标记：

```
<<<<<<< HEAD
你的修改
=======
远程的修改
>>>>>>> origin/master
```

手动编辑文件，选择保留哪个版本，然后：

```powershell
git add .
git commit -m "merge: 解决合并冲突"
git push
```

---

> **文档更新**: 2026-07-11 | **适用项目**: `c:\myobs\`
