"""
Persistent Artifact Registry backed by SQLite.

The registry stores files known to the agent and provides:
- File registration and updates
- Artifact lookup
- Type-based searching
- Content fingerprint lookup
- Missing-file tracking
- Rename handling
- Assignment de-duplication

The database is stored at:
    data/artifacts.db
"""

import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DB_PATH = Path("data/artifacts.db")


# ---------------------------------------------------------
# Database schema
# ---------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    extension TEXT,
    artifact_type TEXT DEFAULT 'unknown',
    size INTEGER,
    mtime REAL,
    content_hash TEXT,
    content_snippet TEXT,
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'discovered',
    first_seen TEXT,
    last_seen TEXT
);

CREATE INDEX IF NOT EXISTS idx_artifacts_name
ON artifacts(name);

CREATE INDEX IF NOT EXISTS idx_artifacts_type
ON artifacts(artifact_type);

CREATE INDEX IF NOT EXISTS idx_artifacts_hash
ON artifacts(content_hash);


CREATE TABLE IF NOT EXISTS seen_assignments (
    coursework_id TEXT PRIMARY KEY,
    course_id TEXT,
    title TEXT,
    first_seen TEXT
);
"""


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def _now():
    """
    Return the current UTC time as an ISO-8601 string.
    """
    return datetime.now(timezone.utc).isoformat()


def _quick_hash(
    path,
    chunk_size=64 * 1024,
    max_bytes=2_000_000
):
    """
    Calculate a partial SHA-256 fingerprint.

    Only the first ~2 MB of the file are hashed.
    This is intentionally NOT treated as a guaranteed
    full-content identity.

    It is useful for inexpensive change/move detection.
    """

    path = Path(path)

    hasher = hashlib.sha256()
    bytes_read = 0

    with open(path, "rb") as file:
        while bytes_read < max_bytes:
            chunk = file.read(
                min(chunk_size, max_bytes - bytes_read)
            )

            if not chunk:
                break

            hasher.update(chunk)
            bytes_read += len(chunk)

    return hasher.hexdigest()


# ---------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------

class ArtifactRegistry:

    def __init__(self, db_path=DB_PATH):
        """
        Create/open the SQLite database.
        """

        self.db_path = Path(db_path)

        # Make sure the database directory exists.
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Open SQLite connection.
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )

        # Return rows as dictionary-like objects.
        self.conn.row_factory = sqlite3.Row

        # Create tables/indexes if they don't exist.
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # =====================================================
    # WRITE OPERATIONS
    # =====================================================

    def register(
        self,
        path,
        artifact_type="unknown",
        source="discovered",
        content_snippet=None
    ):
        """
        Register a file in the artifact registry.

        If the file already exists:
            - update its metadata
            - re-hash only when size or modification time changed
            - mark it active again

        Returns:
            artifact_id
            or None if the file doesn't exist.
        """

        path = Path(path).resolve()

        # File must exist.
        if not path.exists() or not path.is_file():
            return None

        stat = path.stat()

        # Check whether this path is already registered.
        existing = self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE path = ?
            """,
            (str(path),)
        ).fetchone()

        # Only calculate the expensive fingerprint when
        # the file is new or its metadata changed.
        needs_hash = (
            existing is None
            or existing["mtime"] != stat.st_mtime
            or existing["size"] != stat.st_size
        )

        if needs_hash:
            content_hash = _quick_hash(path)
        else:
            content_hash = existing["content_hash"]

        now = _now()

        # -------------------------------------------------
        # Existing artifact
        # -------------------------------------------------

        if existing:

            artifact_id = existing["id"]

            self.conn.execute(
                """
                UPDATE artifacts
                SET
                    name = ?,
                    extension = ?,
                    artifact_type = ?,
                    size = ?,
                    mtime = ?,
                    content_hash = ?,
                    content_snippet =
                        COALESCE(?, content_snippet),
                    status = 'active',
                    source = ?,
                    last_seen = ?
                WHERE path = ?
                """,
                (
                    path.name,
                    path.suffix.lower(),
                    artifact_type,
                    stat.st_size,
                    stat.st_mtime,
                    content_hash,
                    content_snippet,
                    source,
                    now,
                    str(path),
                )
            )

        # -------------------------------------------------
        # New artifact
        # -------------------------------------------------

        else:

            artifact_id = str(uuid.uuid4())

            self.conn.execute(
                """
                INSERT INTO artifacts (
                    id,
                    path,
                    name,
                    extension,
                    artifact_type,
                    size,
                    mtime,
                    content_hash,
                    content_snippet,
                    status,
                    source,
                    first_seen,
                    last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    str(path),
                    path.name,
                    path.suffix.lower(),
                    artifact_type,
                    stat.st_size,
                    stat.st_mtime,
                    content_hash,
                    content_snippet,
                    "active",
                    source,
                    now,
                    now,
                )
            )

        self.conn.commit()

        return artifact_id

    # -----------------------------------------------------

    def mark_missing(self, path):
        """
        Mark an artifact as missing.

        The database row is retained because the file may
        later be restored or used for historical tracking.
        """

        path = Path(path).resolve()

        self.conn.execute(
            """
            UPDATE artifacts
            SET
                status = 'missing',
                last_seen = ?
            WHERE path = ?
            """,
            (
                _now(),
                str(path),
            )
        )

        self.conn.commit()

    # -----------------------------------------------------

    def rename(self, old_path, new_path):
        """
        Preserve artifact identity when a file is renamed or moved.

        If the destination path already exists in the registry,
        it is treated as a stale registry entry and removed so
        the artifact being moved can retain its original ID.
        """

        old_path = Path(old_path).resolve()
        new_path = Path(new_path).resolve()

        # -----------------------------------------------------
        # Find the artifact being moved
        # -----------------------------------------------------

        source_artifact = self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE path = ?
            """,
            (str(old_path),)
        ).fetchone()

        # Nothing registered at the old path.
        if source_artifact is None:
            return None

        # -----------------------------------------------------
        # Check whether destination already exists in registry
        # -----------------------------------------------------

        destination_artifact = self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE path = ?
            """,
            (str(new_path),)
        ).fetchone()

        # -----------------------------------------------------
        # Remove stale destination record
        # -----------------------------------------------------

        if (
            destination_artifact is not None
            and destination_artifact["id"] != source_artifact["id"]
        ):
            self.conn.execute(
                """
                DELETE FROM artifacts
                WHERE path = ?
                """,
                (str(new_path),)
            )

        # -----------------------------------------------------
        # Preserve the original artifact ID
        # -----------------------------------------------------

        self.conn.execute(
            """
            UPDATE artifacts
            SET
                path = ?,
                name = ?,
                extension = ?,
                status = 'active',
                last_seen = ?
            WHERE id = ?
            """,
            (
                str(new_path),
                new_path.name,
                new_path.suffix.lower(),
                _now(),
                source_artifact["id"],
            )
        )

        self.conn.commit()

        return source_artifact["id"]

    # -----------------------------------------------------

    def find_by_hash(self, content_hash):
        """
        Find active artifacts with the given quick fingerprint.
        """

        return self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE content_hash = ?
              AND status = 'active'
            """,
            (content_hash,)
        ).fetchall()

    # =====================================================
    # READ OPERATIONS
    # =====================================================

    def all_active(self):
        """
        Return all currently active artifacts.
        """

        return self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE status = 'active'
            ORDER BY name
            """
        ).fetchall()

    # -----------------------------------------------------

    def get(self, artifact_id):
        """
        Retrieve one artifact using its ID.
        """

        return self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE id = ?
            """,
            (artifact_id,)
        ).fetchone()

    # -----------------------------------------------------

    def search_by_type(self, artifact_type):
        """
        Search active artifacts by artifact type.

        'unknown' artifacts are also returned because the
        type detector may not always know the exact type.
        """

        return self.conn.execute(
            """
            SELECT *
            FROM artifacts
            WHERE status = 'active'
              AND (
                    artifact_type = ?
                    OR artifact_type = 'unknown'
                  )
            ORDER BY name
            """,
            (artifact_type,)
        ).fetchall()

    # =====================================================
    # ASSIGNMENT DE-DUPLICATION
    # =====================================================

    def has_seen_assignment(self, coursework_id):
        """
        Check whether a Classroom coursework ID has already
        been processed.
        """

        row = self.conn.execute(
            """
            SELECT 1
            FROM seen_assignments
            WHERE coursework_id = ?
            """,
            (coursework_id,)
        ).fetchone()

        return row is not None

    # -----------------------------------------------------

    def mark_assignment_seen(
        self,
        coursework_id,
        course_id,
        title
    ):
        """
        Mark a Classroom assignment as seen.

        INSERT OR IGNORE prevents duplicate records.
        """

        self.conn.execute(
            """
            INSERT OR IGNORE INTO seen_assignments (
                coursework_id,
                course_id,
                title,
                first_seen
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                coursework_id,
                course_id,
                title,
                _now(),
            )
        )

        self.conn.commit()

    # =====================================================
    # CLEANUP
    # =====================================================

    def close(self):
        """
        Close the SQLite connection.
        """

        if self.conn:
            self.conn.close()
            self.conn = None