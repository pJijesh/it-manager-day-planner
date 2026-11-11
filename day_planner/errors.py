"""Exceptions raised by day_planner."""

from __future__ import annotations


class InputError(Exception):
    """Raised when an input file or argument is missing, malformed or inconsistent.

    All problems found are collected so that the person fixing the file can
    correct them in one pass instead of discovering them one run at a time.
    """

    def __init__(self, problems: list[str] | str):
        if isinstance(problems, str):
            problems = [problems]
        self.problems = list(problems)
        super().__init__("; ".join(self.problems[:3]) + (" ..." if len(self.problems) > 3 else ""))

    def format(self, limit: int = 25) -> str:
        if len(self.problems) == 1:
            return f"Error: {self.problems[0]}"
        shown = self.problems[:limit]
        lines = [f"Error: {len(self.problems)} problems found:"]
        lines += [f"  - {p}" for p in shown]
        if len(self.problems) > limit:
            lines.append(f"  ... and {len(self.problems) - limit} more")
        return "\n".join(lines)
