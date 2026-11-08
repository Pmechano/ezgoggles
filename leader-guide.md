# ezgoggles leader guide

You help the group leader set up a group project for ezgoggles. All members will read the map that you write. Most members will not read the code. Read `agent-guide.md` first: its words and rules also apply to you.

Setup is shared work, so these rules apply:

- Do the setup on `main`. You do not need a stage branch or a plan in `activity.json`.
- The leader's own TUI setup (name and mode) is personal. Leave it to the leader.
- Setup is done when `check` prints `OK` and the leader has read the map in the TUI. If the leader is not available, stop after `check` and tell the leader what to review.

## 1. Add ezgoggles

If `ezgoggles/` does not exist, add it as a git submodule. Use a URL that every member can clone, such as the GitHub URL. A local path does not work for members.

```
git submodule add <ezgoggles repo url> ezgoggles
```

Then run `init`:

```
uv run --project ezgoggles ezgoggles init
```

`init` makes these changes. It only adds text. It never deletes or replaces text:

- It creates `goggles-data/.gitignore`, so git ignores the personal files in `goggles-data/.local/`.
- It adds the entry line to `README.md` and `AGENTS.md`.
- It adds `@AGENTS.md` to `CLAUDE.md`.

## 2. Collect the course materials

Put the original course materials in `docs/`. Examples: the assignment, the rubric and the data description. Do not edit them. They are the sources for the map.

If some materials are not in the repo, ask the leader for them.

Only official course materials are sources. Old reports, drafts and notes are not requirements.

If the project already has work in it, do not move or rename existing files unless the leader agrees. A stage `path` can point to an existing directory.

## 3. Design the pipeline with the leader

Read all of `docs/`. Then propose a pipeline to the leader, and change it until the leader agrees.

Keep three layers apart. They answer different questions, and different people own them:

| Layer | Question | Owner | In the map |
|---|---|---|---|
| Task | What does the course ask for? | the teacher | `requirements` |
| Solution | How does the group solve it? | the leader and the group | `stages` |
| Code | How does the program run? | each member's agent | no; see `agent-guide.md` |

The map links the layers. Each deliverable names the stages that make it (`from`). Each stage names its directory (`path`). Members understand the project through these links. At a defense, "why does this stage exist?" has its answer in the task layer.

Cut the stages where the data changes form:

- Do not cut by the parts of the assignment (part 1, part 2). Then the handoffs between stages are not visible.
- Do not cut by script files. Code changes every day, and the map then becomes out of date.
- Put the boundary between two stages at a clear handoff: a file, a table or a function that one stage gives to the next.
- A stage is also a direction. Usually one member takes one stage. So the number of stages is close to the number of directions the group needs. The team size can be unknown: members can take more than one stage.
- The report or the presentation can be a stage.

## 4. Make the directories

Recommended structure. Each item has a reason. Change it to fit the course:

| Directory | Reason |
|---|---|
| `docs/` | The original course materials. Agents read them when they need the exact wording of a requirement. |
| One directory for each stage | When a member understands the map, they also understand the directories. Each member's agent stays in its own directory, so merges have fewer conflicts. |
| `data/` for input data that no stage makes | No stage owns it, so it does not go in a stage directory. |

Write the `path` of each stage in the map.

## 5. Write the map

Write `goggles-data/map.json`. The schema is `ezgoggles/src/ezgoggles/schema/map.schema.json`.

**The map is for understanding, not for reference.** Members read it in the TUI. They must be able to read it comfortably and understand the project. Exact details stay in `docs/` and in the stage directories, where agents read them.

```json
{
  "language": "zh",
  "title": "共享单车需求预测",
  "goal": "预测各站点下周的骑行需求，并写成报告。",
  "requirements": {
    "sources": ["docs/assignment.pdf", "docs/rubric.pdf"],
    "deliver": [
      {"text": "PDF 报告（不超过 10 页）", "due": "2026-12-20", "from": ["report"]},
      {"text": "预测代码", "due": "2026-12-20", "from": ["clean", "model"]},
      {"text": "答辩", "due": "2026-12-22 14:00", "from": ["model", "report"]}
    ],
    "grading": ["模型 40%", "报告 60%"],
    "notes": ["迟交每天扣 10%"]
  },
  "stages": [
    {
      "id": "clean",
      "name": "数据清洗",
      "does": "去掉异常记录，补齐缺失时段",
      "path": "src/clean/",
      "input": "原始骑行记录",
      "output": "汇总表",
      "next": ["model"]
    }
  ]
}
```

- `language`: `zh` unless the leader says otherwise. Members who read in another language get a translation (see `agent-guide.md`).
- `goal`: one sentence. What the project makes.
- `requirements`: key points only, one short line each. Do not copy the original text. If the materials are incomplete or conflict, put the open point in `notes` and tell the leader.
  - `deliver`: one item for each thing that the group hands in. A presentation or a defense is a deliverable too. `text` is a short noun phrase. `due` is the deadline (`YYYY-MM-DD`, or `YYYY-MM-DD HH:MM`); leave it out if there is none. `from` lists the stages whose output goes directly into the deliverable. Do not list earlier stages: the TUI finds them through `next`, and shows "PDF 报告（经 需求预测）" to a member of an earlier stage.
  - `grading`: weights. `notes`: rules that a member must not miss.
  - `sources`: the original files. Readers go there for details.
- `id`: lowercase ASCII. Members' branch names use it.
- `name`: a short name that a person says, not a file name.
- `does`: one short sentence. What the stage does.
- `input` and `output`: a short noun phrase each, for example "汇总表". The TUI shows the output on the arrow to the next stage. Put exact formats (columns, fields, function signatures) in a file in the stage directory. If a handoff file is too big for git, write where members get it in that file.
- `path`: the stage directory. It links the stage to its code, and it limits what an agent changes.

Write for a reader who is new to the project: use the words of the course, not code names, and keep each list short. `check` warns when a text is long for a reader.

Then run `check` until it prints `OK`. `check` validates the structure and the links between the layers, and warns about long text and about a stage whose output goes into no deliverable. It does not check that the key points are correct, so compare them with the originals yourself. Then run `open`, and ask the leader to read the map in the TUI.

## 6. Publish

Commit these files and push them to the group's GitHub organization repo. If there is no remote yet, commit locally and tell the leader to add one.

- `docs/`
- `goggles-data/map.json` and `goggles-data/.gitignore`
- `README.md`, `AGENTS.md` and `CLAUDE.md`
- `.gitmodules` and `ezgoggles`
- the stage directories

Tell the members two things:

- Clone with `git clone --recurse-submodules <url>`. If `ezgoggles/` is empty after a clone, run `git submodule update --init`.
- Install `uv`.

## Later changes to the map

The map changes when the course materials change or when the pipeline changes. Then:

1. Transcribe the changes into the map again.
2. Run `check`.
3. Merge the change into `main` through a pull request. The leader reviews it.
