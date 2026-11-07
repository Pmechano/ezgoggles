import json
import subprocess
from pathlib import Path

import pytest

from ezgoggles.paths import Paths

MAP = {
    "title": "校园共享单车需求预测",
    "goal": "用历史骑行数据预测各站点下周的需求量，并写成报告。",
    "requirements": {
        "sources": ["docs/assignment.md"],
        "content": "## 任务要求\n- 预测下周需求\n## 评分细则\n- 模型 40%\n- 报告 60%",
    },
    "stages": [
        {
            "id": "clean",
            "name": "数据清洗",
            "path": "src/clean/",
            "input": "原始骑行记录 CSV",
            "output": "按站点和小时汇总的表",
            "next": ["model"],
            "detail": "去掉异常记录，补齐缺失的时段。",
        },
        {
            "id": "model",
            "name": "需求预测",
            "path": "src/model/",
            "input": "按站点和小时汇总的表",
            "output": "各站点下周每小时的预测值",
            "next": ["report"],
        },
        {
            "id": "report",
            "name": "报告",
            "path": "report/",
            "input": "预测值",
            "output": "PDF 报告",
            "next": [],
        },
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


def write_activity(paths: Paths, data: dict = ACTIVITY) -> None:
    paths.activity.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
