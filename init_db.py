"""Database schema creation, migration and seed data.

Running ``python init_db.py`` creates or upgrades ``rokitna.db`` safely.  The
module deliberately keeps existing information: tables are created with
``IF NOT EXISTS`` and migrations add only the fields required by newer parts of
the course project.

Requirement 15 adds a durable audit trail.  Every new DecisionLog row records
its author and every matching ChangeHistory row references the exact decision
that caused it.
"""

from __future__ import annotations

from database import get_connection
from models.user import RoleEnum
from utils.hashing import hash_password
from utils.logger import get_logger
from config import BASE_DIR, DEFAULT_PASSWORD

logger = get_logger()

# --------------------------------------------------------------------------- #
# Schema definition
# --------------------------------------------------------------------------- #
SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS SQLQueryLog (
        logId      INTEGER PRIMARY KEY AUTOINCREMENT,
        executedAt TEXT NOT NULL,
        sql        TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Users (
        userId        INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE,
        passwordHash  TEXT NOT NULL,
        plainPassword TEXT,
        role          TEXT NOT NULL,
        isActive      INTEGER NOT NULL DEFAULT 1,
        clientId      INTEGER,
        createdAt     TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (clientId) REFERENCES Clients (clientId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Clients (
        clientId  INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT NOT NULL,
        phone     TEXT NOT NULL,
        email     TEXT NOT NULL,
        status    TEXT NOT NULL DEFAULT 'Active',
        createdAt TEXT NOT NULL DEFAULT (datetime('now')),
        updatedAt TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Projects (
        projectId   INTEGER PRIMARY KEY AUTOINCREMENT,
        clientId    INTEGER NOT NULL,
        projectName TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'Active',
        createdAt   TEXT NOT NULL DEFAULT (datetime('now')),
        updatedAt   TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (clientId) REFERENCES Clients (clientId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS DecisionLog (
        decisionId      INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId       INTEGER NOT NULL,
        createdByUserId INTEGER NOT NULL,
        decisionText    TEXT NOT NULL,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ChangeHistory (
        changeId        INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId       INTEGER NOT NULL,
        decisionId      INTEGER NOT NULL,
        createdByUserId INTEGER NOT NULL,
        description     TEXT NOT NULL,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId),
        FOREIGN KEY (decisionId) REFERENCES DecisionLog (decisionId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ActivityLog (
        activityId INTEGER PRIMARY KEY AUTOINCREMENT,
        entityType TEXT NOT NULL,
        entityId   INTEGER NOT NULL,
        action     TEXT NOT NULL,
        details    TEXT,
        createdAt  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Reports (
        reportId    INTEGER PRIMARY KEY AUTOINCREMENT,
        reportType  TEXT NOT NULL,
        criteria    TEXT,
        status      TEXT NOT NULL DEFAULT 'Saved',
        generatedAt TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Milestones (
        milestoneId INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId   INTEGER NOT NULL,
        title       TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'Pending',
        createdAt   TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS PaymentRequests (
        requestId   INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId   INTEGER NOT NULL,
        amount      REAL NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        status      TEXT NOT NULL DEFAULT 'Open',
        createdAt   TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Payments (
        paymentId   INTEGER PRIMARY KEY AUTOINCREMENT,
        requestId   INTEGER NOT NULL,
        amount      REAL NOT NULL,
        paymentDate TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (requestId) REFERENCES PaymentRequests (requestId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Alerts (
        alertId   INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId INTEGER NOT NULL,
        message   TEXT NOT NULL,
        createdAt TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Meetings (
        meetingId   INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId   INTEGER NOT NULL,
        meetingDate TEXT NOT NULL,
        meetingTime TEXT NOT NULL,
        location    TEXT NOT NULL,
        summary     TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'Proposed',
        createdAt   TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Inquiries (
        inquiryId  INTEGER PRIMARY KEY AUTOINCREMENT,
        clientId   INTEGER NOT NULL,
        content    TEXT NOT NULL,
        targetRole TEXT NOT NULL DEFAULT 'OfficeManager',
        status     TEXT NOT NULL DEFAULT 'Open',
        createdAt  TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (clientId) REFERENCES Clients (clientId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Drawings (
        drawingId       INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId       INTEGER NOT NULL,
        fileName        TEXT NOT NULL,
        storedPath      TEXT NOT NULL,
        description     TEXT NOT NULL DEFAULT '',
        createdByUserId INTEGER NOT NULL,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS FieldNotes (
        noteId          INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId       INTEGER NOT NULL,
        description     TEXT NOT NULL,
        createdByUserId INTEGER NOT NULL,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Changes (
        changeId        INTEGER PRIMARY KEY AUTOINCREMENT,
        projectId       INTEGER NOT NULL,
        description     TEXT NOT NULL,
        cost            REAL NOT NULL DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'Pending',
        createdByUserId INTEGER NOT NULL,
        decidedByUserId INTEGER,
        decidedAt       TEXT,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (projectId) REFERENCES Projects (projectId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Reminders (
        reminderId      INTEGER PRIMARY KEY AUTOINCREMENT,
        message         TEXT NOT NULL,
        targetRole      TEXT NOT NULL,
        targetClientId  INTEGER,
        createdByUserId INTEGER NOT NULL,
        createdAt       TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (targetClientId) REFERENCES Clients (clientId),
        FOREIGN KEY (createdByUserId) REFERENCES Users (userId)
    );
    """,
)


# Demo users seeded on first run: (username, role).
SEED_USERS: tuple[tuple[str, RoleEnum], ...] = (
    ("manager", RoleEnum.OFFICE_MANAGER),
    ("architect", RoleEnum.ARCHITECT),
    ("client", RoleEnum.CLIENT),
)


def _table_columns(connection, table_name: str) -> set[str]:
    """Return existing columns for a table, including legacy databases."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _apply_project_migrations(connection) -> None:
    """Upgrade legacy databases that predate ``Projects.updatedAt``."""
    columns = _table_columns(connection, "Projects")
    if "updatedAt" not in columns:
        connection.execute("ALTER TABLE Projects ADD COLUMN updatedAt TEXT")
        logger.info("DATABASE MIGRATION: Projects.updatedAt added")

    connection.execute(
        """
        UPDATE Projects
        SET updatedAt = COALESCE(updatedAt, createdAt, datetime('now'))
        WHERE updatedAt IS NULL
        """
    )


def _apply_users_migrations(connection) -> None:
    """Add columns to legacy Users tables."""
    cols = _table_columns(connection, "Users")
    if "clientId" not in cols:
        connection.execute("ALTER TABLE Users ADD COLUMN clientId INTEGER")
        logger.info("DATABASE MIGRATION: Users.clientId added")
    if "plainPassword" not in cols:
        connection.execute("ALTER TABLE Users ADD COLUMN plainPassword TEXT")
        logger.info("DATABASE MIGRATION: Users.plainPassword added")


def _apply_collaboration_migrations(connection) -> None:
    """Add columns introduced with the collaboration features to legacy DBs."""
    if "status" not in _table_columns(connection, "Meetings"):
        connection.execute(
            "ALTER TABLE Meetings ADD COLUMN status TEXT NOT NULL DEFAULT 'Proposed'"
        )
        logger.info("DATABASE MIGRATION: Meetings.status added")
    if "description" not in _table_columns(connection, "PaymentRequests"):
        connection.execute(
            "ALTER TABLE PaymentRequests ADD COLUMN description TEXT NOT NULL DEFAULT ''"
        )
        logger.info("DATABASE MIGRATION: PaymentRequests.description added")
    if "targetRole" not in _table_columns(connection, "Inquiries"):
        connection.execute(
            "ALTER TABLE Inquiries ADD COLUMN targetRole TEXT NOT NULL DEFAULT 'OfficeManager'"
        )
        logger.info("DATABASE MIGRATION: Inquiries.targetRole added")


def _apply_reports_migrations(connection) -> None:
    """Add the Requirement 20 report-metadata columns to legacy databases."""
    report_columns = _table_columns(connection, "Reports")
    if "criteria" not in report_columns:
        connection.execute("ALTER TABLE Reports ADD COLUMN criteria TEXT")
        logger.info("DATABASE MIGRATION: Reports.criteria added")
    if "status" not in report_columns:
        connection.execute(
            "ALTER TABLE Reports ADD COLUMN status TEXT NOT NULL DEFAULT 'Saved'"
        )
        logger.info("DATABASE MIGRATION: Reports.status added")


def _apply_requirement_15_migrations(connection) -> None:
    """Add Requirement 15 audit fields to legacy local databases.

    SQLite cannot add a foreign-key constraint or a NOT NULL column with a
    dynamic default using ``ALTER TABLE``.  New databases receive the full
    schema above.  For an existing database, these columns are added and
    historical rows are backfilled with the seeded architect account when it
    exists.  All new rows are inserted through the repository with complete
    values and in one transaction.
    """
    decision_columns = _table_columns(connection, "DecisionLog")
    if "createdByUserId" not in decision_columns:
        connection.execute("ALTER TABLE DecisionLog ADD COLUMN createdByUserId INTEGER")
        logger.info("DATABASE MIGRATION: DecisionLog.createdByUserId added")

    change_columns = _table_columns(connection, "ChangeHistory")
    if "decisionId" not in change_columns:
        connection.execute("ALTER TABLE ChangeHistory ADD COLUMN decisionId INTEGER")
        logger.info("DATABASE MIGRATION: ChangeHistory.decisionId added")
    if "createdByUserId" not in change_columns:
        connection.execute("ALTER TABLE ChangeHistory ADD COLUMN createdByUserId INTEGER")
        logger.info("DATABASE MIGRATION: ChangeHistory.createdByUserId added")

    architect_row = connection.execute(
        "SELECT userId FROM Users WHERE role = ? ORDER BY userId LIMIT 1",
        (RoleEnum.ARCHITECT.value,),
    ).fetchone()
    if architect_row is None:
        return

    architect_id = architect_row["userId"]
    connection.execute(
        """
        UPDATE DecisionLog
        SET createdByUserId = ?
        WHERE createdByUserId IS NULL
        """,
        (architect_id,),
    )
    connection.execute(
        """
        UPDATE ChangeHistory
        SET createdByUserId = ?
        WHERE createdByUserId IS NULL
        """,
        (architect_id,),
    )

    # Best-effort migration of historic entries created by the earlier version:
    # its description format was "נרשמה החלטה מקצועית (#<decisionId>)".
    connection.execute(
        """
        UPDATE ChangeHistory
        SET decisionId = CAST(
            substr(
                description,
                instr(description, '#') + 1,
                instr(substr(description, instr(description, '#') + 1), ')') - 1
            ) AS INTEGER
        )
        WHERE decisionId IS NULL
          AND description LIKE '%#%)%'
        """
    )


def create_tables() -> None:
    """Create all tables and apply non-user-dependent migrations."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)
        _apply_project_migrations(connection)
        _apply_reports_migrations(connection)
        _apply_users_migrations(connection)
        _apply_collaboration_migrations(connection)
        connection.commit()
        logger.info("DATABASE SCHEMA READY")
    finally:
        connection.close()


def seed_users() -> None:
    """Insert demo users, then backfill Requirement 15 audit identities."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        password_hash = hash_password(DEFAULT_PASSWORD)
        for username, role in SEED_USERS:
            cursor.execute(
                "SELECT 1 FROM Users WHERE username = ?", (username,)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO Users (username, passwordHash, role, isActive)
                    VALUES (?, ?, ?, 1)
                    """,
                    (username, password_hash, role.value),
                )
                logger.info("SEED USER CREATED: %s (%s)", username, role.value)

        _apply_requirement_15_migrations(connection)
        connection.commit()
    finally:
        connection.close()


def seed_demo_data() -> None:
    """Insert compact demo content only when the database has no clients."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM Clients")
        if cursor.fetchone()["count"] > 0:
            return

        cursor.execute(
            "INSERT INTO Clients (name, phone, email, status) VALUES (?, ?, ?, 'Active')",
            ("דירת דמו - משפחת כהן", "0501234567", "demo.cohen@example.com"),
        )
        client_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Projects
            (clientId, projectName, status, createdAt, updatedAt)
            VALUES (?, ?, 'Active', datetime('now'), datetime('now'))
            """,
            (client_id, "עיצוב דירת גן"),
        )
        project_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO Milestones (projectId, title, status) VALUES (?, ?, 'InProgress')",
            (project_id, "אישור תוכניות ראשוניות"),
        )
        cursor.execute(
            """
            INSERT INTO PaymentRequests (projectId, amount, description, status)
            VALUES (?, ?, ?, 'Open')
            """,
            (project_id, 12000.0, "תכנון אדריכלי ותוכניות עבודה"),
        )
        request_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Payments (requestId, amount) VALUES (?, ?)",
            (request_id, 4000.0),
        )
        cursor.execute(
            """
            INSERT INTO PaymentRequests (projectId, amount, description, status)
            VALUES (?, ?, ?, 'Open')
            """,
            (project_id, 6000.0, "עבודות חשמל ותאורה"),
        )
        cursor.execute(
            "INSERT INTO Alerts (projectId, message) VALUES (?, ?)",
            (project_id, "נדרש אישור לקוח לבחירת חומרי גמר"),
        )

        # A second active project so the management report aggregates more than
        # one active project during the live demo.
        cursor.execute(
            """
            INSERT INTO Projects
            (clientId, projectName, status, createdAt, updatedAt)
            VALUES (?, ?, 'Active', datetime('now'), datetime('now'))
            """,
            (client_id, "שיפוץ משרד קבלה"),
        )
        second_project_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Milestones (projectId, title, status) VALUES (?, ?, 'Pending')",
            (second_project_id, "בחירת ספקי תאורה"),
        )
        cursor.execute(
            "INSERT INTO PaymentRequests (projectId, amount, status) VALUES (?, ?, 'Open')",
            (second_project_id, 8000.0),
        )
        cursor.execute(
            "INSERT INTO Alerts (projectId, message) VALUES (?, ?)",
            (second_project_id, "אבן דרך מתקרבת למועד היעד"),
        )

        # A completed project: its data must NOT appear in the management
        # report, which collects information from active projects only.
        cursor.execute(
            """
            INSERT INTO Projects
            (clientId, projectName, status, createdAt, updatedAt)
            VALUES (?, ?, 'Completed', datetime('now'), datetime('now'))
            """,
            (client_id, "פרויקט שהושלם (לא ייכלל בדוח)"),
        )
        completed_project_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Milestones (projectId, title, status) VALUES (?, ?, 'Done')",
            (completed_project_id, "מסירת הפרויקט"),
        )

        # Link the demo "client" user to this client record so the client
        # portal can show this client's own projects, meetings and inquiries.
        cursor.execute(
            "UPDATE Users SET clientId = ? WHERE username = 'client'",
            (client_id,),
        )

        # Upcoming meetings for the client's projects (future dates so they
        # appear in the client's "upcoming meetings" list during the demo).
        cursor.execute(
            """
            INSERT INTO Meetings
            (projectId, meetingDate, meetingTime, location, summary, status)
            VALUES (?, date('now', '+5 days'), '10:00', ?, ?, 'Proposed')
            """,
            (project_id, "משרד רוקיטנה", "סקירת תוכניות ובחירת חומרי גמר"),
        )
        cursor.execute(
            """
            INSERT INTO Meetings
            (projectId, meetingDate, meetingTime, location, summary, status)
            VALUES (?, date('now', '+12 days'), '14:30', ?, ?, 'Confirmed')
            """,
            (second_project_id, "אתר הפרויקט", "מדידות והתאמות בשטח"),
        )

        # A sample inquiry already submitted by the client to the office manager.
        cursor.execute(
            """
            INSERT INTO Inquiries (clientId, content, targetRole, status)
            VALUES (?, ?, 'OfficeManager', 'Open')
            """,
            (client_id, "אשמח לעדכון על לוח הזמנים לחדר השינה הראשי."),
        )

        # Architect collaboration content (field note, drawing, change to approve).
        architect_row = cursor.execute(
            "SELECT userId FROM Users WHERE username = 'architect'"
        ).fetchone()
        architect_id = architect_row["userId"] if architect_row else None
        if architect_id is not None:
            cursor.execute(
                """
                INSERT INTO FieldNotes (projectId, description, createdByUserId)
                VALUES (?, ?, ?)
                """,
                (project_id, "נמדד הפרש גובה של 3 ס\"מ ברצפת הסלון, נדרשת התאמה.", architect_id),
            )
            cursor.execute(
                """
                INSERT INTO Changes (projectId, description, cost, status, createdByUserId)
                VALUES (?, ?, ?, 'Pending', ?)
                """,
                (project_id, "הגדלת חלון הסלון לרוחב 2.4 מ' לצורך תאורה טבעית.", 3500.0, architect_id),
            )

            # A demo drawing: write a small placeholder file and record it.
            drawings_dir = BASE_DIR / "drawings"
            drawings_dir.mkdir(parents=True, exist_ok=True)
            drawing_path = drawings_dir / "demo_living_room_plan.txt"
            drawing_path.write_text(
                "סרטוט הדגמה — תוכנית סלום (קובץ דמו)\n",
                encoding="utf-8",
            )
            cursor.execute(
                """
                INSERT INTO Drawings
                (projectId, fileName, storedPath, description, createdByUserId)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    "תוכנית_סלון.txt",
                    str(drawing_path),
                    "תוכנית ראשונית לסלון",
                    architect_id,
                ),
            )

        # A reminder from the office manager to the client.
        manager_row = cursor.execute(
            "SELECT userId FROM Users WHERE username = 'manager'"
        ).fetchone()
        if manager_row is not None:
            cursor.execute(
                """
                INSERT INTO Reminders
                (message, targetRole, targetClientId, createdByUserId)
                VALUES (?, 'Client', ?, ?)
                """,
                ("תזכורת: נא לאשר את בחירת חומרי הגמר עד סוף השבוע.", client_id, manager_row["userId"]),
            )

        connection.commit()
        logger.info("SEED DEMO DATA CREATED")
    finally:
        connection.close()


def initialize_database() -> None:
    """Run schema creation, migrations, user seeding and initial demo data."""
    create_tables()
    seed_users()
    seed_demo_data()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully at rokitna.db")
