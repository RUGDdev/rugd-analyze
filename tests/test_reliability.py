"""Backup, rollback, concurrency, and closed HTTP sockets. The default database is never written."""

from __future__ import annotations

import gc
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock
import urllib.request
import warnings
from pathlib import Path

from app.reliability import (
    MULTI_INSTANCE_LIMIT,
    BackupError,
    backup_database,
    integrity_report,
    restore_database,
)
from app.server import make_server
from app.store import DEFAULT_DB, connect

ROOT = Path(__file__).resolve().parent.parent


def _insert(connection: sqlite3.Connection, assessment_id: str) -> None:
    now = "2026-11-11T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO assessments (
            id, business_name, purpose, tier, read_only, hypothetical,
            pilot_label, profile_json, review_requested, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assessment_id,
            "Recovery Cafe",
            "startup_feasibility",
            "explore",
            0,
            1,
            "test",
            "{}",
            0,
            now,
            now,
        ),
    )


def _count(path: Path) -> int:
    connection = connect(path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM assessments").fetchone()[0])
    finally:
        connection.close()


class ReliabilityTests(unittest.TestCase):
    def test_interrupted_write_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analyze.sqlite"
            connection = connect(path)
            try:
                with self.assertRaises(RuntimeError):
                    with connection:
                        _insert(connection, "rolled-back")
                        raise RuntimeError("stopped")
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except sqlite3.ProgrammingError:
                        pass
            self.assertEqual(_count(path), 0)

    def test_restart_keeps_a_committed_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analyze.sqlite"
            connection = connect(path)
            _insert(connection, "kept")
            connection.commit()
            connection.close()
            self.assertEqual(_count(path), 1)
            self.assertEqual(integrity_report(path), "ok")

    def test_concurrent_writes_both_persist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analyze.sqlite"
            ready = connect(path)
            ready.close()
            barrier = threading.Barrier(2)
            errors: list[BaseException] = []

            def write(assessment_id: str) -> None:
                try:
                    barrier.wait(timeout=5)
                    local = connect(path)
                    try:
                        _insert(local, assessment_id)
                        local.commit()
                    finally:
                        local.close()
                except BaseException as exc:  # noqa: BLE001 — the test records the worker failure
                    errors.append(exc)

            threads = [
                threading.Thread(target=write, args=("one",)),
                threading.Thread(target=write, args=("two",)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertEqual(errors, [])
            self.assertEqual(_count(path), 2)

    def test_backup_and_restore_round_trip_on_a_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite"
            connection = connect(source)
            _insert(connection, "original")
            connection.commit()
            connection.close()
            copy = Path(directory) / "copy.sqlite"
            backup_database(source, copy)
            changed = connect(source)
            _insert(changed, "later")
            changed.commit()
            changed.close()
            restored = Path(directory) / "restored.sqlite"
            restore_database(copy, restored)
            self.assertEqual(_count(restored), 1)
            self.assertEqual(_count(source), 2)
            self.assertFalse((Path(directory) / "restored.sqlite.partial").exists())

    def test_restore_refuses_the_default_database(self) -> None:
        before = DEFAULT_DB.stat().st_mtime_ns if DEFAULT_DB.exists() else None
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite"
            connection = connect(source)
            _insert(connection, "original")
            connection.commit()
            connection.close()
            copy = Path(directory) / "copy.sqlite"
            backup_database(source, copy)
            with self.assertRaises(BackupError) as caught:
                restore_database(copy, DEFAULT_DB)
            self.assertEqual(caught.exception.category, "refused")
            self.assertNotIn(str(DEFAULT_DB), str(caught.exception))
        after = DEFAULT_DB.stat().st_mtime_ns if DEFAULT_DB.exists() else None
        self.assertEqual(before, after)

    def test_corrupt_file_is_not_restored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.sqlite"
            broken.write_bytes(b"not a database")
            destination = Path(directory) / "destination.sqlite"
            with self.assertRaises(BackupError) as caught:
                restore_database(broken, destination)
            self.assertEqual(caught.exception.category, "integrity")
            self.assertFalse(destination.exists())
            self.assertFalse(Path(str(destination) + ".partial").exists())

    def test_failed_copy_removes_the_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite"
            connection = connect(source)
            _insert(connection, "original")
            connection.commit()
            connection.close()
            destination = Path(directory) / "destination.sqlite"

            def fail_copy(source_path: Path, partial_path: Path) -> None:
                partial_path.write_bytes(b"partial")
                raise sqlite3.OperationalError("disk I/O error")

            with mock.patch("app.reliability._copy", fail_copy):
                with self.assertRaises(BackupError) as caught:
                    backup_database(source, destination)
            self.assertEqual(caught.exception.category, "io")
            self.assertNotIn("disk", str(caught.exception))
            self.assertFalse(destination.exists())
            self.assertFalse(Path(str(destination) + ".partial").exists())

    def test_multi_instance_limit_is_documented(self) -> None:
        text = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
        self.assertIn(MULTI_INSTANCE_LIMIT, text)

    def test_dropped_server_closes_its_listening_socket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "analyze.sqlite"
            connect(database).close()
            server = make_server(database, port=0)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                del server
                gc.collect()
            leaked = [
                item
                for item in caught
                if issubclass(item.category, ResourceWarning) and "socket" in str(item.message)
            ]
            self.assertEqual(leaked, [])

    def test_request_socket_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "analyze.sqlite"
            connect(database).close()
            server = make_server(database, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            host, port = server.server_address
            try:
                gc.collect()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", ResourceWarning)
                    response = urllib.request.urlopen(f"http://{host}:{port}/")
                    response.read()
                    del response
                    gc.collect()
                leaked = [
                    item
                    for item in caught
                    if issubclass(item.category, ResourceWarning) and "socket" in str(item.message)
                ]
                self.assertEqual(leaked, [])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
