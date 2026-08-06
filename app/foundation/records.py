from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,15}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_record_code(prefix: str, sequence: int, *, width: int = 6) -> str:
    normalized = prefix.strip().upper()
    if not _CODE_RE.fullmatch(normalized):
        raise ValueError("prefix must contain 2-16 uppercase letters, digits or underscores")
    if sequence < 1:
        raise ValueError("sequence must be positive")
    if width < 1 or width > 12:
        raise ValueError("width must be between 1 and 12")
    return f"{normalized}-{sequence:0{width}d}"


@dataclass(frozen=True, slots=True)
class RecordState:
    version: int = 1
    is_archived: bool = False
    archived_at: datetime | None = None
    archived_by: str | None = None

    def archive(self, *, actor_id: str, at: datetime | None = None) -> "RecordState":
        if self.is_archived:
            return self
        return RecordState(
            version=self.version + 1,
            is_archived=True,
            archived_at=at or utcnow(),
            archived_by=actor_id,
        )
