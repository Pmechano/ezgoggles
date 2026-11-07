from __future__ import annotations

from ...context import Context
from .base import MarkdownPanel


class RequirementsPanel(MarkdownPanel):
    key = "requirements"

    @staticmethod
    def markdown(ctx: Context) -> str:
        req = ctx.map["requirements"]
        out = req["content"].rstrip()
        if req["sources"]:
            files = ", ".join(f"`{p}`" for p in req["sources"])
            out += f"\n\n---\n\n*{ctx.t('map.sources')}: {files}*"
        return out
