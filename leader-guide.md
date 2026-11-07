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

- A stage is also a direction. Usually one member takes one stage. So the number of stages is close to the number of directions the group needs. The team size can be unknown: members can take more than one stage.
- Put the boundary between two stages at a clear handoff: a file, a table or a function that one stage gives to the next.
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

```json
{
  "title": "Campus bike demand forecast",
  "goal": "Forecast next week's demand at each station from the ride history, and write a report.",
  "requirements": {
    "sources": ["docs/assignment.pdf", "docs/rubric.pdf"],
    "content": "## Requirements\n- ...\n## Rubric\n- ..."
  },
  "stages": [
    {
      "id": "clean",
      "name": "Data cleaning",
      "path": "src/clean/",
      "input": "Raw ride records, CSV (data/rides/)",
      "output": "A table of rides per station per hour",
      "next": ["model"],
      "detail": "Remove broken records. Fill the missing hours."
    }
  ]
}
```

- `requirements.content`: transcribe the requirements and the rubric faithfully. You can change the layout. Do not remove any requirement, any number or any deadline. Members see this text first. If the materials are incomplete or conflict, do not guess: write the open points under the heading `Open questions` at the end, and tell the leader.
- `requirements.sources`: list the files that you transcribed.
- `goal`: one or two sentences.
- `id`: lowercase ASCII. Members' branch names use it.
- `input` and `output`: one short line each, so that a member understands the handoff at a glance. Name the file or the object, and where it is. Put exact formats (columns, fields, function signatures) in a file in the stage directory, and name that file here. If a handoff file is too big for git, write where members get it.
- `detail`: how the stage works inside, and why. Only learning mode shows it.
- Write in the language of the course materials. The TUI language setting changes only the interface. It does not translate the map.

Then run `check` until it prints `OK`. `check` validates only the structure. It does not check that the transcription is faithful, so compare it with the originals yourself. Then run `open`, and ask the leader to read the map in the TUI.

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
