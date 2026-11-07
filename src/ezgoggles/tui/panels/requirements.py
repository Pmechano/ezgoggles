from __future__ import annotations

from ...context import Context
from .base import MarkdownPanel

# Conclusion first: what to hand in, then when, then how it is graded.
GROUPS = ("deliver", "deadlines", "grading", "notes")


class RequirementsPanel(MarkdownPanel):
    key = "requirements"

    @staticmethod
    def markdown(ctx: Context) -> str:
        req = ctx.map["requirements"]
        lines: list[str] = []
        for group in GROUPS:
            items = req.get(group) or []
            if items:
                lines += [f"**{ctx.t(f'requirements.{group}')}**", ""]
                lines += [f"- {it}" for it in items]
                lines.append("")
        if req["sources"]:
            files = ", ".join(f"`{p}`" for p in req["sources"])
            lines.append(f"*{ctx.t('map.sources')}: {files}*")
        return "\n".join(lines).rstrip()
