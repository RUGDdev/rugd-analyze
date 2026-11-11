"""Local SQLite backup, restore, and integrity checks.

A backup reads a database and writes a different file. Restore refuses the
default application database. One process should own the live file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.store import DEFAULT_DB, connect

MULTI_INSTANCE_LIMIT = (
    "One SQLite file supports one application process. "
    "A second process can fail a write or see a stale page. "
    "Keep the service at one instance."
)


class BackupError(RuntimeError):
    """A backup or restore failure reduced to a category. SQL text is not kept."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"database backup failed: {category}")


def integrity_report(path: Path) -> str:
    """Return the SQLite integrity result, or a short category when the file cannot be read."""
    if not path.is_file():
        return "missing"
    connection = sqlite3.connect(path)
    try:
        try:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError:
            return "unreadable"
    finally:
        connection.close()
    return str(row[0] if row else "unreadable")


def backup_database(source: Path, destination: Path) -> None:
    """Copy source to destination. The default application database cannot be the destination."""
    _refuse_protected(destination)
    if not source.is_file():
        raise BackupError("missing")
    if integrity_report(source) != "ok":
        raise BackupError("integrity")
    _copy_checked(source, destination)


def restore_database(backup: Path, destination: Path) -> None:
    """Replace a non-default destination with a checked backup. The live default file is refused."""
    _refuse_protected(destination)
    if not backup.is_file():
        raise BackupError("missing")
    if integrity_report(backup) != "ok":
        raise BackupError("integrity")
    _copy_checked(backup, destination)


def _refuse_protected(path: Path) -> None:
    if path.resolve() == DEFAULT_DB.resolve():
        raise BackupError("refused")


def _copy_checked(source: Path, destination: Path) -> None:
    partial = destination.with_name(destination.name + ".partial")
    try:
        _copy(source, partial)
        if integrity_report(partial) != "ok":
            raise BackupError("integrity")
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial.replace(destination)
    except BackupError:
        partial.unlink(missing_ok=True)
        raise
    except (sqlite3.Error, OSError):
        partial.unlink(missing_ok=True)
        raise BackupError("io") from None


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    source_connection = connect(source)
    try:
        copied = sqlite3.connect(destination)
        try:
            source_connection.backup(copied)
        finally:
            copied.close()
    finally:
        source_connection.close()
