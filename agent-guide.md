# ezgoggles agent guide

You work in a student group project. ezgoggles helps every member understand the project. It is a tool for understanding, not for supervision. Follow this guide in every work session.

## Words

- **Map**: `goggles-data/map.json`. It links two layers. The task layer (`requirements`) is what the course asks for. The solution layer (`stages`) is how the group solves it: the stages, what each stage does, and the handoffs between stages. Each deliverable names the stages that make it. It is written for members to understand, not as a reference. The leader owns the map.
- **Code flow**: the third layer, `goggles-data/.local/code.json`. For the user's stage, the files that the data goes through, in order. Personal, and only in learning mode.
- **Stage**: one step of the pipeline. A stage is also a direction. Usually one member takes one stage. A member can take more than one stage, with one branch for each.
- **Handoff**: what a stage takes from the stages before it, and what it gives to the stages after it.
- **TUI**: a terminal window with tabs. It shows the map, the code flow and your plans to the user. It does not change project files. It writes only the user's personal state in `goggles-data/.local/`. You never control it.

## Commands

Run all commands from the project root:

```
uv run --project ezgoggles ezgoggles <command>
```

| Command | Use |
|---|---|
| `open` | Start the TUI if it is not running. It prints the state of the map, the user and the branch. |
| `check` | Validate `map.json`, the translations, `activity.json` and `code.json`. Run it after each write to `goggles-data/`. |
| `tui` | Run the TUI in the current terminal. The user can run it by hand when no window opens. |
| `init` | Leader setup only. See `leader-guide.md`. |

All commands accept `--root <dir>` when you do not run them from the project root. Example: `uv run --project <project>/ezgoggles ezgoggles --root <project> check`.

`check` validates the structure of these files. It does not check that handoff files exist or that a stage runs.

If the shell does not find `uv`, try `python -m uv`. If that also fails, ask the user to install uv: https://docs.astral.sh/uv/getting-started/installation/

## Start of each session

If you set up the project for the leader, follow `leader-guide.md`. The steps in this section do not apply to that setup.

1. Run `open`. Read its output.
   - `setup is not finished`: ask the user to finish the setup page in the TUI window. Then run `open` again.
   - `map.json does not exist`: if the user is the leader, follow `leader-guide.md`. If not, tell the user to ask the leader for the map.
   - `could not open a window`: give the user the printed command.
   - `no window, because EZGOGGLES_NO_WINDOW is set`: continue your work. The user starts the TUI by hand when they want it.
   - `translation: ...`: the user reads the map in another language. Do the translation first (see below).
2. Read `goggles-data/map.json`. It has the key points only. For exact requirements, read the originals listed in `requirements.sources`. Read `goggles-data/.local/user.json` for the user's `name`, `mode` and `language`.
3. Find the stage. The branch name is `<name>/<stage-id>`, and `open` prints it.
   - If the user is not on a stage branch, ask which stage they take.
   - Update `main` first, if the team uses a remote.
   - Switch to `<name>/<stage-id>`. Create the branch from `main` if it does not exist. If it exists, merge `main` into it.
4. Before you change code, write a plan in `activity.json` (see below). Then run `check`.

## Plans: `goggles-data/.local/activity.json`

The TUI shows this file to the user as a tree: stage → plan → items. The file is personal. Git ignores it.

```json
{
  "clean": [
    {
      "time": "2026-11-07T14:20",
      "title": "Fill missing hours with the mean of the hours around them",
      "items": [
        { "text": "Find the missing hours", "done": true },
        { "text": "Write the fill function", "done": true },
        { "text": "Write a test for the fill function", "done": false, "byUser": true }
      ],
      "summary": "Missing hours now get the mean of the hour before and the hour after. Before, they got 0.",
      "handoffChange": "none"
    }
  ]
}
```

- Add a new plan for each piece of work. Put it under the stage id. Keep the old plans.
- The user must read the plan comfortably. The title says what the work achieves, in one short line. Each item is one short step in the user's words, not in code names.
- Aim for 3 to 7 items in a plan. `check` rejects more than 9.
- When you finish an item, set `done` to `true`.
- When the work ends, write `summary` and `handoffChange`. The summary describes your work. Leave `byUser` items undone until the user does them.
- Schema: `ezgoggles/src/ezgoggles/schema/activity.schema.json`.

## Translating the map

The map is written in one language (`language` in `map.json`, usually `zh`). If the user's `language` is different, `open` prints a `translation:` line. Then:

1. Copy `goggles-data/map.json` to `goggles-data/translations/map.<language>.json`.
2. Translate the text: `title`, `goal`, the requirement items (for a deliverable, only `text`), and each stage's `name`, `does`, `input` and `output`.
3. Do not change `id`, `path`, `next`, `sources`, or a deliverable's `due` and `from`.
4. Set `language` to the user's language, and `source` to the fingerprint that `open` prints.
5. Run `check`.

The translation is shared: commit it with your work. All members who read that language then see the same text.

## Handoffs

A handoff change is the one thing that the user must know.

- A handoff changes when the input or the output of the stage changes. Examples: a file format, column names, a file location, or a function that another stage calls.
- If your work changes a handoff, tell the user in the chat. Also write the change in `handoffChange`.
- If no handoff changes, write `"none"`.
- If your work needs a change in another stage, do not make that change. Tell the user to speak with the member who owns that stage.
- If an input from an upstream stage does not exist yet, use a small sample with the same format. In the summary, say what you could not test with real input.

## Scope

- Change only the files in your stage's `path`. Before you change a file outside it, tell the user and get approval. Exceptions: you write `activity.json` and `code.json` in `goggles-data/.local/`, and translations in `goggles-data/translations/`.
- Do not change `ezgoggles/`.
- Do not change `map.json`. The only exception: the user is the leader and asks for the change. After the change, run `check`.
- Make small commits. Merge into `main` through a pull request, or in the way that the team agreed.

## Modes

The user selects the mode in the TUI. Read it from `user.json`.

- **`learn`**: the user wants to learn while they build.
  - Explain what you do and why.
  - In each plan, mark one or two items with `"byUser": true`. Pick items that teach the user something about the stage.
  - Do not do `byUser` items yourself unless the user asks you to. If the user asks for help, give a hint before you give the answer.
  - Keep the code flow of the user's stage up to date (see below).
- **`deliver`**: you can do the work. The user must still understand the map, their stage and the handoffs. Explain the handoffs. Do not explain internals unless the user asks.

## Code flow: `goggles-data/.local/code.json`

Learning mode only. The TUI shows it in the Code tab: the stage input, then each file, then the stage output. It shows how the data goes through the code of the user's stage. The file is personal. Git ignores it.

```json
{
  "clean": {
    "time": "2026-11-08T10:00",
    "steps": [
      { "file": "src/clean/load.py", "does": "Read the raw rides and drop broken rows" },
      { "file": "src/clean/fill.py::fill_gaps", "does": "Fill missing hours with the mean of the hours around them" },
      { "file": "src/clean/export.py", "does": "Write the summary table" }
    ]
  }
}
```

- Write it the first time you work on the stage in learning mode. Read the code first.
- Update it when your work changes the path of the data. Update `time` too.
- Each step is one file, in the order that the data goes through. Add `::name` when one function is the important part.
- `does` says what the step does to the data, in one short sentence. Do not describe the code line by line.
- Aim for 3 to 7 steps. `check` rejects more than 9.
- Schema: `ezgoggles/src/ezgoggles/schema/code.schema.json`.

## Questions

The user can ask you about the project. Answer with the map in mind: tell the user which stage the answer is about and which handoff it touches.

The map is a transcription and can contain errors. If a question needs the exact wording of a requirement, read the original file in `docs/`.

## Writing style

Text for people must be easy to read. This includes plans, summaries, handoff changes and answers. The TUI shows plans and summaries directly to the user. Use the rules of ASD-STE100 (Simplified Technical English):

- One sentence gives one instruction or one fact.
- Use one word for one thing. Do not change to a synonym.
- Put the conclusion first.
- Use the active voice. Put conditions before actions.
- Use lists for complex content. Do not write long sentences.
- In Chinese: do not use empty verbs like "进行" or "实施". Do not chain many "的".

A Chinese summary of the rules is in `ezgoggles/ASD-STE100.md`. Read it when you need more detail. Write in the user's `language`: `zh` is Chinese and `en` is English.

## Files

| File | Who writes it | Committed |
|---|---|---|
| `goggles-data/map.json` | the leader's agent | yes |
| `goggles-data/translations/map.<language>.json` | the agent of a member who reads that language | yes |
| `goggles-data/.local/user.json` | the TUI. Read it, do not write it. | no |
| `goggles-data/.local/activity.json` | you | no |
| `goggles-data/.local/code.json` | you, in learning mode | no |
| `goggles-data/.local/seen.json` | the TUI: what the user saw on each tab | no |
| `goggles-data/.local/tui.pid` | `open` and the TUI | no |
