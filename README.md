# ezgoggles

ezgoggles 帮小组作业里的每个人看清一张"地图"：项目在做什么，分成哪几段，自己负责哪一段，和谁交接。

它面向用 agent 写代码（vibe coding）的本科小组。它是帮助理解的工具，不是监督工具。

## 它做什么

- **给 agent 一份统一的协作指南**：[agent-guide.md](agent-guide.md)。组员的 agent 每次开工都会读它。Claude Code、Codex 等 harness 都能用。
- **给人一个 TUI**：一个带标签页的终端窗口。标签按"为什么 → 怎么做 → 里面怎么跑 → 现在"排列：
  1. **任务**：要交什么、什么时候交、由哪些段产出
  2. **流程**：项目分成哪几段，交接写在两段之间的箭头上；选中的段展开成卡片
  3. **代码**：你那段代码里，数据依次经过哪些文件（只在学习模式）
  4. **Agent**：agent 正在做什么

  每个标签上有一句状态，例如"交接变了""还有 12 天"，不点开也知道值不值得看。第一次打开时，引导会从左到右走一遍。

项目分三层：任务（老师要什么）、解答（小组怎么做）、代码（程序怎么跑）。"理解项目"指看懂前两层和它们之间的连接，不要求读懂代码。

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
3. 第一次打开时，在 TUI 中设置语言、名字、模式和主题。动效默认开，音效默认关，都可以在设置里切换。
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
| `check` | 校验 `map.json`、翻译、`activity.json` 和 `code.json`。 |
| `init` | 组长初始化：创建 `goggles-data/`，并写入口说明。只追加内容，不删改已有内容。 |

## 小组项目中的文件

```
README.md, AGENTS.md   入口说明（init 写入）
CLAUDE.md              @AGENTS.md
docs/                  课程原始材料
ezgoggles/             本 plugin（submodule，不要修改）
goggles-data/
  map.json             地图：任务层和解答层，以及它们的连接，写给人读懂（提交）
  translations/        地图的其他语言版本，由 agent 翻译（提交）
  .local/              个人状态（git 忽略）
    user.json          名字、模式、语言、主题、动效、音效、引导进度
    activity.json      agent 的计划和进度
    code.json          代码层：你那段的代码流程（学习模式）
    seen.json          每个标签上次看到的内容，用来显示"有变化"
```

TUI 只读 agent 转写过的 JSON，不解析原始材料。各段的进度（`[x]` main 上已有 / `[~]` 有未合并的工作 / `[ ]` 还没有内容）直接从 git 读出，不需要任何人另写。

## 开发

```
uv sync
uv run pytest
```

需要 Python 3.11 以上（uv 会自动准备）。

### 扩展点

核心只做一件事：把文件和 git 状态加载成一个 `Context`（[context.py](src/ezgoggles/context.py)）。其他功能都挂在下面的注册表上，加功能不用改核心：

| 扩展点 | 怎么加 |
|---|---|
| TUI 视图（标签页） | 在 `src/ezgoggles/tui/views/` 写一个 `View` 子类，加进 `VIEWS`。列表顺序就是标签和引导的顺序。可选：`modes`（哪些模式显示）、`token`/`status`（标签状态）、`entered`（打开时的动效）、`move`（↑↓）。 |
| 界面语言或文案风格 | 在 `src/ezgoggles/locales/` 放一个 `.toml`。设置 `base` 可以继承另一种语言，只改部分文案。 |
| 开窗方式 | 在 `src/ezgoggles/launch/launchers.py` 写一个 `Launcher` 子类，加进 `LAUNCHERS`。 |
| 校验规则 | 在 `src/ezgoggles/check.py` 写一个规则函数，加进 `MAP_RULES`、`ACTIVITY_RULES` 或 `CODE_RULES`。 |
| 音效 | 在 `src/ezgoggles/tui/sound.py` 的 `CUES` 加一个事件；新平台的播放方式写成 `Player` 子类，加进 `PLAYERS`。 |
