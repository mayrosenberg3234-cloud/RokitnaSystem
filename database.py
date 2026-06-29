"""SQLite connection management.

A thin helper that yields configured :class:`sqlite3.Connection` objects.  Row
results are returned as :class:`sqlite3.Row` so callers can access columns by
name, and foreign keys are enabled on every connection.

SQL Query Log
-------------
Every SQL statement executed through ``get_connection`` / ``connection_scope``
is persisted to the ``SQLQueryLog`` table so the log survives server restarts.
A separate *log connection* (no trace callback) is used for all writes to that
table, preventing infinite recursion.  A thread-local flag guards against
re-entrant calls when Streamlit serves multiple users concurrently.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from config import DB_PATH


# ---------------------------------------------------------------------------
# Query log data class
# ---------------------------------------------------------------------------

@dataclass
class QueryLogEntry:
    executed_at: str
    sql: str


# ---------------------------------------------------------------------------
# Internal log helpers
# ---------------------------------------------------------------------------

# Thread-local flag: True while we are writing a log entry, so the trace
# callback that fires on *that* write does not recurse into itself.
_logging_active = threading.local()


def _is_relevant_sql(sql: str) -> bool:
    """Return True for SQL statements worth showing in the UI."""
    stripped = sql.strip().lower()
    if not stripped:
        return False
    # Infrastructure noise — never interesting to the user
    if stripped.startswith("pragma"):
        return False
    if stripped in {"begin", "commit", "rollback"}:
        return False
    if stripped.startswith(("savepoint", "release")):
        return False
    # Schema setup — only runs on first launch
    if stripped.startswith(("create table", "create index")):
        return False
    if stripped.startswith(("insert or ignore", "alter table")):
        return False
    # Our own log table — must never be logged (prevents infinite recursion)
    if "sqlquerylog" in stripped:
        return False
    return True


def _get_log_connection() -> sqlite3.Connection:
    """Return a plain connection with NO trace callback.

    All writes to SQLQueryLog use this connection so the trace callback on
    the *application* connection never fires again while we are saving a row.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # No set_trace_callback here — that is intentional.
    return conn


def _ensure_log_table() -> None:
    """Create SQLQueryLog if it does not exist yet.

    Called once at module import time so the table is always present before
    the first application query arrives.
    """
    try:
        conn = _get_log_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS SQLQueryLog (
                    logId      INTEGER PRIMARY KEY AUTOINCREMENT,
                    executedAt TEXT NOT NULL,
                    sql        TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # Silently skip if DB is not yet accessible


# Ensure the table exists as soon as this module is imported.
_ensure_log_table()


# ---------------------------------------------------------------------------
# Trace callback — called by SQLite on every statement
# ---------------------------------------------------------------------------

def _record_sql_query(sql: str) -> None:
    """Persist one SQL statement to SQLQueryLog.

    Safety guarantees:
    * Re-entrant calls (from the log-connection's own writes) are blocked by
      the thread-local ``_logging_active`` flag.
    * Exceptions are swallowed so a logging failure never breaks the app.
    * All writes use ``_get_log_connection`` (no trace callback) to avoid
      infinite recursion.
    """
    if not _is_relevant_sql(sql):
        return
    if getattr(_logging_active, "active", False):
        return

    _logging_active.active = True
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = _get_log_connection()
        try:
            conn.execute(
                "INSERT INTO SQLQueryLog (executedAt, sql) VALUES (?, ?)",
                (now, sql),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
    finally:
        _logging_active.active = False


# ---------------------------------------------------------------------------
# Public log API
# ---------------------------------------------------------------------------

def get_query_log(limit: int = 200) -> list[QueryLogEntry]:
    """Return the most recent *limit* queries, newest first.

    Reads from the persistent ``SQLQueryLog`` table so entries survive server
    restarts.  Falls back to an empty list if the table is not yet available.
    """
    try:
        conn = _get_log_connection()
        try:
            rows = conn.execute(
                "SELECT executedAt, sql FROM SQLQueryLog ORDER BY logId DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                QueryLogEntry(executed_at=r["executedAt"], sql=r["sql"])
                for r in rows
            ]
        finally:
            conn.close()
    except Exception:
        return []


def clear_query_log() -> None:
    """Delete all entries from SQLQueryLog."""
    if getattr(_logging_active, "active", False):
        return
    _logging_active.active = True
    try:
        conn = _get_log_connection()
        try:
            conn.execute("DELETE FROM SQLQueryLog")
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
    finally:
        _logging_active.active = False


# ---------------------------------------------------------------------------
# Application connection factory
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection configured for the application."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.set_trace_callback(_record_sql_query)
    return connection


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    """Context manager that commits on success and rolls back on error."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
