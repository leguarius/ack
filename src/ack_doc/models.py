"""Structures de données internes (TEC-026 à TEC-028)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PageText:
    number: int
    text: str


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    relative_path: Path
    anack: str
    ornum: int
    exsum: str


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    file: str | None = None
    page: int | None = None
    tag: str | None = None

    def to_dict(self, *, include_file: bool = False) -> dict[str, object]:
        data: dict[str, object] = {"code": self.code, "message": self.message}
        if include_file and self.file is not None:
            data["file"] = self.file
        if self.tag is not None:
            data["tag"] = self.tag
        if self.page is not None:
            data["page"] = self.page
        return data


@dataclass
class ValidationResult:
    documents: list[SourceDocument] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass
class DocumentAnalysis:
    """Résultat de l'analyse d'un PDF source, avant la validation croisée."""

    path: Path
    relative_path: str
    anack: str | None = None
    ornum: int | None = None
    exsum: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def to_source_document(self) -> SourceDocument:
        assert self.is_valid and self.anack is not None
        assert self.ornum is not None and self.exsum is not None
        return SourceDocument(
            path=self.path,
            relative_path=Path(self.relative_path),
            anack=self.anack,
            ornum=self.ornum,
            exsum=self.exsum,
        )
