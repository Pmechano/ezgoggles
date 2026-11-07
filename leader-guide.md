# ezgoggles leader guide

You help the group leader set up a group project for ezgoggles. All members will read the map that you write. Most members will not read the code. Read `agent-guide.md` first: its words and rules also apply to you.

## 1. Add ezgoggles

If `ezgoggles/` does not exist, add it as a git submodule:

```
git submodule add <ezgoggles repo url> ezgoggles
```

Then run `init`:

```
uv run --project ezgoggles ezgoggles init
```

`init` makes these changes. It never overwrites a file:

- It creates `goggles-data/.gitignore`, so git ignores the personal files in `goggles-data/.local/`.
- It adds the entry line to `README.md` and `AGENTS.md`.
- It adds `@AGENTS.md` to `CLAUDE.md`.

## 2. Collect the course materials

Put the original course materials in `docs/`. Examples: the assignment, the rubric and the data description. Do not edit them. They are the sources for the map.

If some materials are not in the repo, ask the leader for them.

## 3. Design the pipeline with the leader

Read all of `docs/`. Then propose a pipeline to the leader, and change it until the leader agrees.

- A stage is also a direction. One member takes one stage. So the number of stages is close to the number of directions the group needs.
- Put the boundary between two stages at a clear handoff: a file, a table or a function that one stage gives to the next.
- The report or the presentation can be a stage.

## 4. Make the directories

Recommended structure. Each item has a reason. Change it to fit the course:

| Directory | Reason |
|---|---|
| `docs/` | The original course materials. Agents compare their work with these files in every session. |
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

- `requirements.content`: transcribe the requirements and the rubric faithfully. You can change the layout. Do not remove any requirement, any number or any deadline. Members see this text first.
- `requirements.sources`: list the files that you transcribed.
- `goal`: one or two sentences.
- `id`: lowercase ASCII. Members' branch names use it.
- `input` and `output`: describe the handoff exactly enough for the next stage to use it.
- `detail`: how the stage works inside, and why. Only learning mode shows it.
- Write in the language of the course materials.

Then run `check` until it prints `OK`. Run `open`, and ask the leader to read the map in the TUI.

## 6. Publish

Commit these files and push them to the group's GitHub organization repo:

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
