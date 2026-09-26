"""Offline file snapshots and a replaceable SQLite FTS5 search index."""

import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from urllib.parse import quote


class RetrievalError(Exception):
    """An expected input or local index error suitable for CLI display."""


_APPLICATION_ID = 0x4E454D4F  # NEMO
_SCHEMA_VERSION = 1
_WORDS = re.compile(r"\w+(?:-\w+)*", re.UNICODE)
_QUERY_PARTS = re.compile(r'"([^"]*)"|([^\s"]+)')
_IDENTIFIERS = re.compile(r"\b[A-Za-z]+-\d+\b")
_STOPWORDS = {
    "a", "an", "and", "are", "do", "for", "how", "in", "is", "of", "on",
    "the", "to", "was", "were", "what", "where", "who", "why",
}


@contextmanager
def _directory_fd(path: Path) -> Iterator[int]:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        descriptor = os.open("/", flags)
        stack.callback(os.close, descriptor)
        for part in path.parts[1:]:
            descriptor = os.open(part, flags, dir_fd=descriptor)
            stack.callback(os.close, descriptor)
        yield descriptor


def _read_source(root_fd: int, relative: str) -> bytes:
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(part in {".", ".."} for part in path.parts):
        raise ValueError("source path must stay within the selected root")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        parent_fd = root_fd
        for part in path.parts[:-1]:
            parent_fd = os.open(part, flags, dir_fd=parent_fd)
            stack.callback(os.close, parent_fd)
        file_fd = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=parent_fd)
        stack.callback(os.close, file_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise OSError("source is not a regular file")
        with os.fdopen(file_fd, "rb", closefd=False) as handle:
            return handle.read()


def _documents(root: str):
    chosen = Path(root)
    if chosen.is_symlink() or not chosen.is_dir():
        raise RetrievalError(f"root must be an existing, non-symlink directory: {chosen}")
    boundary = chosen.resolve()

    def walk_error(error: OSError) -> None:
        raise RetrievalError(f"cannot traverse selected root {boundary}: {error}") from error

    try:
        with _directory_fd(boundary) as root_fd:
            for directory, names, files in os.walk(boundary, followlinks=False, onerror=walk_error):
                parent = Path(directory)
                names[:] = sorted(
                    name for name in names
                    if not (parent / name).is_symlink()
                    and (parent / name).resolve().is_relative_to(boundary)
                )
                for name in sorted(files):
                    path = parent / name
                    if path.suffix not in {".md", ".txt"} or path.is_symlink() or not path.is_file():
                        continue
                    if not path.resolve().is_relative_to(boundary):
                        continue
                    try:
                        relative = path.relative_to(boundary).as_posix()
                        raw = _read_source(root_fd, relative)
                        lines = raw.decode("utf-8").splitlines()
                    except (OSError, UnicodeError, ValueError) as exc:
                        raise RetrievalError(f"cannot read UTF-8 source {path}: {exc}") from exc
                    yield relative, "sha256:" + hashlib.sha256(raw).hexdigest(), lines
    except OSError as exc:
        raise RetrievalError(f"cannot traverse selected root {boundary}: {exc}") from exc


def _check_index(connection: sqlite3.Connection) -> None:
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if application_id != _APPLICATION_ID or version != _SCHEMA_VERSION:
        raise RetrievalError("database is not a supported Nemo index")
    required = {"metadata", "sources", "passages", "passage_fts"}
    found = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    )}
    if not required <= found:
        raise RetrievalError("Nemo index schema is incomplete or corrupt")


def index_directory(root: str, db: str) -> dict[str, int]:
    # Read the complete selected snapshot before changing the persistent index.
    sources = list(_documents(root))
    db_path = Path(db)
    temporary_path = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{db_path.name}.", suffix=".tmp",
                                          dir=db_path.parent)
        temporary_path = Path(name)
        os.close(descriptor)
        with closing(sqlite3.connect(temporary_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DROP TABLE IF EXISTS passage_fts")
            connection.execute("DROP TABLE IF EXISTS passages")
            connection.execute("DROP TABLE IF EXISTS sources")
            connection.execute("DROP TABLE IF EXISTS metadata")
            connection.execute("CREATE TABLE metadata (root TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata(root) VALUES (?)", (str(Path(root).resolve()),))
            connection.execute("CREATE TABLE sources (path TEXT PRIMARY KEY, revision TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE passages (id INTEGER PRIMARY KEY, path TEXT NOT NULL "
                "REFERENCES sources(path), start_line INTEGER NOT NULL, "
                "end_line INTEGER NOT NULL, text TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE VIRTUAL TABLE passage_fts USING fts5("
                "text, content='passages', content_rowid='id', tokenize='unicode61')"
            )
            passages = 0
            for path, revision, lines in sources:
                connection.execute("INSERT INTO sources(path, revision) VALUES (?, ?)", (path, revision))
                for line_number, line in enumerate(lines, 1):
                    if not line.strip():
                        continue
                    connection.execute(
                        "INSERT INTO passages(path, start_line, end_line, text) VALUES (?, ?, ?, ?)",
                        (path, line_number, line_number, line),
                    )
                    passages += 1
            connection.execute("INSERT INTO passage_fts(passage_fts) VALUES ('rebuild')")
            connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        if db_path.is_symlink():
            raise RetrievalError(f"cannot replace symlink index {db_path}")
        if db_path.exists():
            uri = "file:" + quote(str(db_path.resolve()), safe="/") + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as existing:
                _check_index(existing)
        os.replace(temporary_path, db_path)
        temporary_path = None
    except (OSError, sqlite3.Error) as exc:
        raise RetrievalError(f"cannot write Nemo index {db_path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return {"files": len(sources), "passages": passages}


def _match_expression(query: str) -> str:
    clauses: list[str] = []
    for quoted, bare in _QUERY_PARTS.findall(query):
        words = _WORDS.findall(quoted or bare)
        if not words:
            continue
        if bare and len(words) == 1 and words[0].casefold() in _STOPWORDS:
            continue
        if bare and len(words) > 1:
            clauses.extend(f'"{word}"' for word in words if word.casefold() not in _STOPWORDS)
        else:
            clauses.append('"' + " ".join(word.replace("-", " ") for word in words) + '"')
    return " OR ".join(clauses)


def _current_source_lines(root: Path, relative: str, revision: str) -> list[str] | None:
    try:
        with _directory_fd(root) as root_fd:
            raw = _read_source(root_fd, relative)
        if "sha256:" + hashlib.sha256(raw).hexdigest() != revision:
            return None
        return raw.decode("utf-8").splitlines()
    except (OSError, UnicodeError, ValueError):
        return None


def search_index(query: str, db: str) -> list[dict]:
    db_path = Path(db)
    if not db_path.is_file():
        raise RetrievalError(f"Nemo index does not exist: {db_path}")
    expression = _match_expression(query)
    try:
        # Read-only URI prevents search from creating or modifying an index.
        uri = "file:" + quote(str(db_path.resolve()), safe="/") + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            _check_index(connection)
            metadata = connection.execute("SELECT root FROM metadata").fetchone()
            if metadata is None or not isinstance(metadata[0], str) or not Path(metadata[0]).is_absolute():
                raise RetrievalError("Nemo index source metadata is missing or corrupt")
            root = Path(metadata[0])
            if not expression:
                return []
            rows = connection.execute(
                "SELECT p.path, p.start_line, p.end_line, s.revision, p.text, "
                "bm25(passage_fts) FROM passage_fts "
                "JOIN passages AS p ON p.id = passage_fts.rowid "
                "JOIN sources AS s ON s.path = p.path "
                "WHERE passage_fts MATCH ?",
                (expression,),
            ).fetchall()
    except (OSError, sqlite3.Error) as exc:
        raise RetrievalError(f"cannot read Nemo index {db_path}: {exc}") from exc

    identifiers = {match.group().casefold() for match in _IDENTIFIERS.finditer(query)}
    hits = []
    source_lines: dict[str, list[str] | None] = {}
    for path, start, end, revision, passage, bm25_score in rows:
        if path not in source_lines:
            source_lines[path] = _current_source_lines(root, path, revision)
        lines = source_lines[path]
        if (lines is None or not isinstance(start, int) or not isinstance(end, int)
                or start < 1 or end < start or end > len(lines)
                or "\n".join(lines[start - 1:end]) != passage):
            continue
        # SQLite FTS5 BM25 is negative: more relevant passages have lower values.
        # An exact identifier in the cited line resolves close document distractors.
        identifier_boost = 100 if identifiers.intersection(
            match.group().casefold() for match in _IDENTIFIERS.finditer(passage)
        ) else 0
        score = float(bm25_score) - identifier_boost
        if not math.isfinite(score):
            raise RetrievalError("index returned a non-finite ranking score")
        hits.append({"path": path, "start_line": start, "end_line": end,
                     "revision": revision, "text": passage, "score": score})
    hits.sort(key=lambda hit: (hit["score"], hit["path"], hit["start_line"]))
    return hits


def evaluate_fixture(fixture_dir: str) -> dict:
    fixture = Path(fixture_dir)
    query_path = fixture / "queries.json"
    try:
        queries = json.loads(query_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RetrievalError(f"cannot read fixture queries {query_path}: {exc}") from exc
    if not isinstance(queries, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("query"), str)
        or not isinstance(item.get("relevant_paths"), list)
        or any(not isinstance(path, str) for path in item["relevant_paths"])
        for item in queries
    ):
        raise RetrievalError("queries.json must be an array of id, query, relevant_paths records")

    recall_values = []
    ndcg_values = []
    unanswerable = false_hits = 0
    with tempfile.TemporaryDirectory(prefix="nemo-evaluate-") as temporary:
        db = str(Path(temporary) / "index.sqlite")
        index_directory(str(fixture / "documents"), db)
        for item in queries:
            hits = search_index(item["query"], db)
            ranked_paths = list(dict.fromkeys(hit["path"] for hit in hits))[:10]
            relevant = set(item["relevant_paths"])
            if not relevant:
                unanswerable += 1
                false_hits += bool(hits)
                continue
            recall_values.append(len(relevant.intersection(ranked_paths)) / len(relevant))
            dcg = sum(1 / math.log2(rank + 2) for rank, path in enumerate(ranked_paths) if path in relevant)
            ideal = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(relevant))))
            ndcg_values.append(dcg / ideal)
    return {
        "query_count": len(queries),
        "recall_at_10": sum(recall_values) / len(recall_values) if recall_values else 0.0,
        "ndcg_at_10": sum(ndcg_values) / len(ndcg_values) if ndcg_values else 0.0,
        "unanswerable_count": unanswerable,
        "unanswerable_false_hits": false_hits,
    }
