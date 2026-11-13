"""The source record every provider import must produce before it is indexed.

A source is the authoritative unit a passage cites: one Slack message, meeting note or
document, identified by its provider-native ID inside a tenant. Titles and paths are
display data and never identify a source. The tenant is a scope label supplied with the
import. It is not authentication.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit


class SourceError(Exception):
    """A source record or manifest that does not satisfy the contract."""


_PROVIDER = re.compile(r"[a-z][a-z0-9_-]*")
_REQUIRED = ("provider", "native_id", "tenant", "path", "title")
_OPTIONAL = ("author", "created_at", "uri", "visibility")


@dataclass(frozen=True)
class SourceRecord:
    provider: str
    native_id: str
    tenant: str
    path: str
    title: str
    author: str | None = None
    created_at: str | None = None
    uri: str | None = None
    visibility: str | None = None

    @property
    def id(self) -> str:
        """Canonical ID. Each part is percent-encoded so a ':' or '/' inside one cannot collide."""
        return ":".join(quote(part, safe="") for part in (self.provider, self.tenant, self.native_id))


def file_source(relative_path: str) -> SourceRecord:
    """A plainly indexed local file. Nothing beyond its path and name is known, so nothing is guessed."""
    return SourceRecord(
        provider="file",
        native_id=relative_path,
        tenant="local",
        path=relative_path,
        title=PurePosixPath(relative_path).name,
    )


def _record(item: object, position: int) -> SourceRecord:
    where = f"source {position}"
    if not isinstance(item, dict):
        raise SourceError(f"{where} must be an object")
    unknown = sorted(set(item) - set(_REQUIRED) - set(_OPTIONAL))
    if unknown:
        raise SourceError(f"{where} has unknown field(s): {', '.join(unknown)}")
    values: dict[str, str | None] = {}
    for key in _REQUIRED + _OPTIONAL:
        value = item.get(key)
        if value is None and key in _OPTIONAL:
            values[key] = None  # absent stays absent; it is never filled in
            continue
        if not isinstance(value, str) or not value.strip():
            raise SourceError(f"{where} needs a non-empty string for {key!r}")
        values[key] = value

    provider, created_at, uri = values["provider"], values["created_at"], values["uri"]
    if provider is None or not _PROVIDER.fullmatch(provider):
        raise SourceError(f"{where} provider must look like 'slack' or 'notion'")
    if created_at is not None:
        try:
            moment = datetime.fromisoformat(created_at)
        except ValueError as exc:
            raise SourceError(f"{where} created_at is not an ISO 8601 time: {created_at!r}") from exc
        if moment.tzinfo is None:
            raise SourceError(f"{where} created_at needs a UTC offset: {created_at!r}")
    if uri is not None:
        parts = urlsplit(uri)
        if not parts.scheme or not parts.netloc:
            raise SourceError(f"{where} uri must be absolute, with a scheme: {uri!r}")
    return SourceRecord(**values)  # type: ignore[arg-type]  # required keys were checked above


def load_manifest(manifest: str) -> list[SourceRecord]:
    """Read explicitly listed sources. Any invalid or duplicate record rejects the whole manifest."""
    path = Path(manifest)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"cannot read source manifest {path}: {exc}") from exc
    if not isinstance(data, list):
        raise SourceError(f"source manifest {path} must be a JSON array of source records")
    records = []
    seen: set[str] = set()
    for position, item in enumerate(data, 1):
        try:
            record = _record(item, position)
        except SourceError as exc:
            raise SourceError(f"source manifest {path}: {exc}") from exc
        if record.id in seen:
            raise SourceError(f"source manifest {path}: duplicate source ID {record.id}")
        seen.add(record.id)
        records.append(record)
    return records
