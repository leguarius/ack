"""Journal JSON (TEC-046 à TEC-050, TEC-095)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ack_doc import __version__, errors
from ack_doc.models import DocumentAnalysis, ValidationIssue

SCHEMA_VERSION = "1.0"

_STATUS = {
    errors.EXIT_SUCCESS: "success",
    errors.EXIT_VALIDATION: "validation_failed",
    errors.EXIT_TECHNICAL: "execution_failed",
}


@dataclass
class JournalData:
    started_at: datetime
    duration_seconds: float = 0.0
    exit_code: int = errors.EXIT_SUCCESS
    analyses: list[DocumentAnalysis] = field(default_factory=list)
    global_issues: list[ValidationIssue] = field(default_factory=list)


def build_journal(data: JournalData) -> dict[str, object]:
    files = []
    for analysis in data.analyses:
        files.append(
            {
                "path": analysis.relative_path,
                "status": "conforme" if analysis.is_valid else "non_conforme",
                "errors": [i.to_dict() for i in analysis.issues],
            }
        )
    valid = sum(1 for a in data.analyses if a.is_valid)
    return {
        "schema_version": SCHEMA_VERSION,
        "application_version": __version__,
        "started_at": data.started_at.isoformat(timespec="seconds"),
        "duration_seconds": round(data.duration_seconds, 2),
        "status": _STATUS[data.exit_code],
        "pdf_count": len(data.analyses),
        "valid_count": valid,
        "invalid_count": len(data.analyses) - valid,
        "files": files,
        "errors": [i.to_dict(include_file=True) for i in data.global_issues],
    }


def write_journal(path: Path, data: JournalData) -> None:
    """Remplace le journal de façon atomique."""
    payload = json.dumps(build_journal(data), ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=".ack-doc-journal-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
