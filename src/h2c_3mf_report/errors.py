"""Typed errors and ProblemDetails-style envelopes for h2c_3mf_report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROBLEM_BASE = "https://paperclip.local/problems/h2c-3mf-report"


@dataclass
class ReportProblem(Exception):
    code: str
    message: str
    http_status: int = 400
    title: str | None = None

    def __post_init__(self) -> None:  # pragma: no cover - dataclass exception plumbing
        Exception.__init__(self, self.message)

    def to_dict(self) -> dict[str, Any]:
        return problem(self.code, self.message, self.http_status, self.title)


class InvalidArchiveError(ReportProblem):
    def __init__(self, message: str = "Input is not a readable ZIP/3MF archive.") -> None:
        super().__init__("INVALID_ARCHIVE", message, 400, "Invalid archive")


class UnsafeArchiveEntryError(ReportProblem):
    def __init__(self, message: str = "Archive contains an unsafe member path.") -> None:
        super().__init__("INVALID_ARCHIVE", message, 400, "Invalid archive")


class XmlParseReportError(ReportProblem):
    def __init__(self, message: str = "Metadata/slice_info.config is not parseable XML.") -> None:
        super().__init__("XML_PARSE_ERROR", message, 400, "Invalid slice_info.config")


class ConfigReportError(ReportProblem):
    def __init__(self, message: str) -> None:
        super().__init__("CONFIG_ERROR", message, 400, "Invalid configuration")


def problem(code: str, message: str, http_status: int = 400, title: str | None = None) -> dict[str, Any]:
    normalized = code.lower().replace("_", "-")
    return {
        "type": f"{PROBLEM_BASE}/{normalized}",
        "title": title or code.replace("_", " ").title(),
        "status": http_status,
        "code": code,
        "detail": message,
        # Keep architecture-friendly short key too.
        "message": message,
    }


def warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}
