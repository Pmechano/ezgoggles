"""The panel registry. The main screen shows these panels, and opens them one by one in this order."""

from __future__ import annotations

from .activity import ActivityPanel
from .base import MarkdownPanel, Panel
from .project_map import MapPanel
from .requirements import RequirementsPanel
from .stage import StagePanel

PANELS: list[type[Panel]] = [
    RequirementsPanel,
    MapPanel,
    StagePanel,
    ActivityPanel,
]

__all__ = ["PANELS", "Panel", "MarkdownPanel"]
