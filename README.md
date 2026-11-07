# ezgoggles

ezgoggles 帮小组作业里的每个人看清一张"地图"：项目在做什么，分成哪几段，自己负责哪一段，和谁交接。

它面向用 agent 写代码（vibe coding）的本科小组。它是帮助理解的工具，不是监督工具。

## 它做什么

- **给 agent 一份统一的协作指南**：[agent-guide.md](agent-guide.md)。组员的 agent 每次开工都会读它。Claude Code、Codex 等 harness 都能用。
- **给人一个 TUI**：一个终端窗口，一步一步展示四块内容：
  1. 任务要求
  2. 项目地图（pipeline 的各段和交接）
  3. 我的段
  4. agent 正在做什么

"理解项目"指看懂数据流和交接，不要求读懂代码。

## 准备

安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

## 组长

1. 在小组项目里导入 ezgoggles：

   ```
   git submodule add <ezgoggles 仓库地址> ezgoggles
   ```

2. 让你的 agent 阅读 `ezgoggles/leader-guide.md` 并照做。agent 会读 `docs/` 中的课程材料，和你一起设计 pipeline，然后写出地图 `goggles-data/map.json`。
3. 在 TUI 中检查地图，然后发布到 GitHub organization repo。

## 组员

1. clone 项目：

   ```
   git clone --recurse-submodules <项目地址>
   ```

2. 像平常一样让 agent 干活。agent 会读到入口说明，然后自动打开 TUI。
3. 第一次打开时，在 TUI 中设置语言、名字、模式和主题。
   - **学习模式**：边做边学。agent 会多解释，并留一部分工作给你做。
   - **交付模式**：agent 多做一些。你仍需要看懂整个项目。
4. 有问题直接问你的 agent。

TUI 可以正常关闭。agent 下次开工时会重新打开它。

## 命令

在项目根目录运行：

```
uv run --project ezgoggles ezgoggles <命令>
```

| 命令 | 作用 |
|---|---|
| `open` | TUI 没有运行时，在新窗口中打开它。支持 Windows、macOS、Ubuntu，以及从 WSL 打开到 Windows 一侧。 |
| `tui` | 在当前终端中运行 TUI。 |
| `check` | 校验 `map.json` 和 `activity.json`。 |
| `init` | 组长初始化：创建 `goggles-data/`，并写入口说明。只追加内容，不删改已有内容。 |

## 小组项目中的文件

```
README.md, AGENTS.md   入口说明（init 写入）
CLAUDE.md              @AGENTS.md
docs/                  课程原始材料
ezgoggles/             本 plugin（submodule，不要修改）
goggles-data/
  map.json             地图（提交）
  .local/              个人状态（git 忽略）
    user.json          名字、模式、语言、主题、看到第几步
    activity.json      agent 的计划和进度
```

TUI 只读 agent 转写过的 JSON，不解析原始材料。

## 开发

```
uv sync
uv run pytest
```
