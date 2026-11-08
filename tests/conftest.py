import json
import subprocess
from pathlib import Path

import pytest

from ezgoggles.paths import Paths

MAP = {
    "language": "zh",
    "title": "共享单车需求预测",
    "goal": "预测各站点下周的骑行需求，并写成报告。",
    "requirements": {
        "sources": ["docs/assignment.md"],
        "deliver": [
            {"text": "PDF 报告", "due": "2026-12-20", "from": ["report"]},
            {"text": "预测代码", "due": "2026-12-20", "from": ["clean", "model"]},
            {"text": "答辩", "due": "2026-12-22 14:00", "from": ["model", "report"]},
        ],
        "grading": ["模型 40%", "报告 60%"],
    },
    "stages": [
        {
            "id": "clean",
            "name": "数据清洗",
            "does": "去掉异常记录，补齐缺失时段",
            "path": "src/clean/",
            "input": "原始骑行记录",
            "output": "汇总表",
            "next": ["model"],
        },
        {
            "id": "model",
            "name": "需求预测",
            "does": "训练模型，预测下周需求",
            "path": "src/model/",
            "input": "汇总表",
            "output": "预测值",
            "next": ["report"],
        },
        {
            "id": "report",
            "name": "报告",
            "does": "把结果写成报告",
            "path": "report/",
            "input": "预测值",
            "output": "PDF 报告",
            "next": [],
        },
    ],
}

MAP_EN = {
    **MAP,
    "language": "en",
    "title": "Bike demand forecast",
    "goal": "Forecast next week's demand at each station, and write a report.",
    "requirements": {
        "sources": ["docs/assignment.md"],
        "deliver": [
            {"text": "PDF report", "due": "2026-12-20", "from": ["report"]},
            {"text": "Forecast code", "due": "2026-12-20", "from": ["clean", "model"]},
            {"text": "Defense", "due": "2026-12-22 14:00", "from": ["model", "report"]},
        ],
        "grading": ["Model 40%", "Report 60%"],
    },
    "stages": [
        dict(MAP["stages"][0], name="Cleaning", does="Remove bad records, fill gaps", input="Raw rides", output="Summary table"),
        dict(MAP["stages"][1], name="Forecast", does="Train a model, forecast demand", input="Summary table", output="Forecasts"),
        dict(MAP["stages"][2], name="Report", does="Write up the results", input="Forecasts", output="PDF report"),
    ],
}

ACTIVITY = {
    "clean": [
        {
            "time": "2026-11-07T14:20",
            "title": "缺失时段改用前后均值填充",
            "items": [
                {"text": "找出缺失时段", "done": True},
                {"text": "给填充函数写测试", "done": False, "byUser": True},
            ],
        }
    ]
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def project(tmp_path: Path) -> Paths:
    root = tmp_path / "proj"
    for d in ("docs", "src/clean", "src/model", "report", "goggles-data/.local"):
        (root / d).mkdir(parents=True)
    (root / "docs/assignment.md").write_text("assignment", encoding="utf-8")
    (root / "goggles-data/map.json").write_text(json.dumps(MAP, ensure_ascii=False), encoding="utf-8")
    _git(root, "init", "-b", "main")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "init")
    return Paths(root)


CODE = {
    "model": {
        "time": "2026-11-08T10:00",
        "steps": [
            {"file": "src/model/features.py", "does": "按站点算出过去 24 小时的特征"},
            {"file": "src/model/train.py::fit", "does": "训练模型，存下参数"},
        ],
    }
}


def write_code(paths: Paths, data: dict = CODE) -> None:
    paths.code.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_activity(paths: Paths, data: dict = ACTIVITY) -> None:
    paths.activity.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
