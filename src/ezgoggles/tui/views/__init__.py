"""The view registry. Each view is one tab. The order is the order of the tabs and of the tour:
why (task), how (flow), how inside (code), and now (agent)."""

from __future__ import annotations

from .agent import AgentView
from .base import Status, View
from .code import CodeView
from .flow import FlowView
from .task import TaskView

VIEWS: list[type[View]] = [
    TaskView,
    FlowView,
    CodeView,
    AgentView,
]

HOME = "flow"  # the tab that opens after the tour

__all__ = ["VIEWS", "HOME", "View", "Status"]
