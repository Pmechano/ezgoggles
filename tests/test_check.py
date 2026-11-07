import codecs
import json

from conftest import ACTIVITY, MAP, write_activity

from ezgoggles.check import MAP_RULES, check_activity, check_map
from ezgoggles.cli import cmd_check


def test_valid_map(project):
    r = check_map(project)
    assert r.ok, r.errors
    assert r.warnings == []


def test_missing_map(project):
    project.map.unlink()
    r = check_map(project)
    assert not r.ok and "does not exist" in r.errors[0]


def test_broken_json(project):
    project.map.write_text("{ nope", encoding="utf-8")
    r = check_map(project)
    assert "not valid JSON" in r.errors[0]


def test_schema_and_semantic_errors(project):
    bad = json.loads(json.dumps(MAP))
    bad["stages"][0]["id"] = "Clean!"
    bad["stages"][1]["next"] = ["nowhere"]
    bad["extra"] = 1
    project.map.write_text(json.dumps(bad), encoding="utf-8")
    r = check_map(project)
    assert not r.ok
    assert any("Clean!" in e for e in r.errors)
    assert any("extra" in e for e in r.errors)


def test_unknown_next_and_duplicates(project):
    bad = json.loads(json.dumps(MAP))
    bad["stages"][1]["next"] = ["nowhere"]
    bad["stages"][2]["id"] = "model"
    project.map.write_text(json.dumps(bad), encoding="utf-8")
    r = check_map(project)
    assert any("'nowhere'" in e for e in r.errors)
    assert any("more than once" in e for e in r.errors)


def test_missing_path_is_warning(project):
    (project.root / "report").rmdir()
    r = check_map(project)
    assert r.ok and any("report/" in w for w in r.warnings)


def test_activity(project):
    ids = {s["id"] for s in MAP["stages"]}
    assert check_activity(project, ids).data == {}
    write_activity(project)
    assert check_activity(project, ids).ok
    write_activity(project, {"ghost": ACTIVITY["clean"]})
    r = check_activity(project, ids)
    assert r.ok and any("ghost" in w for w in r.warnings)


def test_finished_plan_needs_handoff(project):
    plan = {"time": "2026-11-07T10:00", "title": "x", "items": [{"text": "a", "done": True}]}
    write_activity(project, {"clean": [plan]})
    r = check_activity(project, {"clean"})
    assert any("handoffChange" in w for w in r.warnings)


def test_bom_is_accepted(project):
    write_activity(project)
    project.activity.write_bytes(codecs.BOM_UTF8 + project.activity.read_bytes())
    assert check_activity(project, {"clean"}).ok


def test_null_map_is_an_error(project):
    project.map.write_text("null", encoding="utf-8")
    r = check_map(project)
    assert not r.ok and "not of type 'object'" in r.errors[0]


def test_cycle_is_warning(project):
    loop = json.loads(json.dumps(MAP))
    loop["stages"][2]["next"] = ["clean"]
    project.map.write_text(json.dumps(loop), encoding="utf-8")
    r = check_map(project)
    assert r.ok
    assert any("clean -> model -> report -> clean" in w for w in r.warnings)


def test_long_text_only_warns(project):
    long = json.loads(json.dumps(MAP))
    long["stages"][0]["does"] = "去掉异常记录" * 10
    long["requirements"]["grading"] = [f"第 {i} 条" for i in range(9)]
    project.map.write_text(json.dumps(long, ensure_ascii=False), encoding="utf-8")
    r = check_map(project)
    assert r.ok
    assert any("stages/clean/does: long for a reader" in w for w in r.warnings)
    assert any("requirements/grading: 9 items" in w for w in r.warnings)


def test_translation_checks(project):
    from conftest import MAP_EN

    from ezgoggles.check import check_translation
    from ezgoggles.model import fingerprint

    project.translations.mkdir()
    f = project.translation("en")
    f.write_text(json.dumps(dict(MAP_EN, source=fingerprint(MAP))), encoding="utf-8")
    r = check_translation(project, "en", MAP)
    assert r.ok and not r.stale, r.errors
    broken = json.loads(json.dumps(MAP_EN))
    broken["stages"][0]["path"] = "elsewhere/"
    f.write_text(json.dumps(broken), encoding="utf-8")
    r = check_translation(project, "en", MAP)
    assert any("source: missing" in e for e in r.errors)
    assert any("ids, paths and next" in e for e in r.errors)


def test_rules_are_pluggable(project, monkeypatch):
    def no_report_stage(m, paths, r):
        if any(s["id"] == "report" for s in m["stages"]):
            r.errors.append("custom: report is not allowed")

    monkeypatch.setattr("ezgoggles.check.MAP_RULES", [*MAP_RULES, no_report_stage])
    r = check_map(project)
    assert r.errors == ["custom: report is not allowed"] and r.data is None


def test_check_command_exit_code(project, capsys):
    assert cmd_check(project) == 0
    project.map.write_text("[]", encoding="utf-8")
    assert cmd_check(project) == 1
    assert "ERROR goggles-data/map.json" in capsys.readouterr().out
