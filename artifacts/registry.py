from pathlib import Path
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "artifacts.db"
)

def _utc_now():

    return datetime.now(timezone.utc).isoformat()


def _quick_hash(
    path,
    chunk_size=64 * 1024,
    max_bytes=2_000_000,
):

    path = Path(path)

    hasher = hashlib.sha256()
    total_read = 0

    with path.open("rb") as file:
        while total_read < max_bytes:
            remaining = max_bytes - total_read
            chunk = file.read(
                min(chunk_size, remaining)
            )

            if not chunk:
                break

            hasher.update(chunk)
            total_read += len(chunk)

    return hasher.hexdigest()


class ArtifactRegistry:

    def __init__(self, db_path=DB_PATH):


        self._lock = threading.Lock()


        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )

        self.conn.row_factory = sqlite3.Row


        self._create_tables()


    def _create_tables(self):

        with self._lock:

            self.conn.executescript(
                """
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

                CREATE INDEX IF NOT EXISTS
                    idx_artifacts_name
                    ON artifacts(name);

                CREATE INDEX IF NOT EXISTS
                    idx_artifacts_type
                    ON artifacts(artifact_type);

                CREATE INDEX IF NOT EXISTS
                    idx_artifacts_hash
                    ON artifacts(content_hash);

                CREATE TABLE IF NOT EXISTS seen_assignments (
                    coursework_id TEXT PRIMARY KEY,
                    course_id TEXT,
                    title TEXT,
                    first_seen TEXT
                );
                """
            )

            self.conn.commit()


    def _generate_artifact_id(
        self,
        path,
        content_hash,
    ):

        value = (
            f"{Path(path).resolve()}|"
            f"{content_hash}"
        )

        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:16]


    def register(
        self,
        path,
        artifact_type="unknown",
        source="discovered",
        content_snippet=None,
    ):

        path = Path(path).resolve()


        if not path.exists():
            print(
                f"[registry] File does not exist: {path}"
            )
            return None

        if not path.is_file():
            print(
                f"[registry] Path is not a file: {path}"
            )
            return None


        try:
            stat = path.stat()

        except OSError as error:
            print(
                f"[registry] Could not stat {path}: "
                f"{error}"
            )
            return None

        size = stat.st_size
        mtime = stat.st_mtime

        path_str = str(path)
        name = path.name
        extension = path.suffix.lower()


        with self._lock:

            existing = self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE path = ?
                """,
                (path_str,),
            ).fetchone()


            needs_hash = (
                existing is None
                or existing["size"] != size
                or existing["mtime"] != mtime
                or not existing["content_hash"]
            )

            if needs_hash:

                try:
                    content_hash = _quick_hash(path)

                except OSError as error:
                    print(
                        f"[registry] Could not hash {path}: "
                        f"{error}"
                    )
                    return None

            else:
                content_hash = existing[
                    "content_hash"
                ]


            if existing:

                artifact_id = existing["id"]

                self.conn.execute(
                    """
                    UPDATE artifacts

                    SET
                        path = ?,
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

                    WHERE id = ?
                    """,
                    (
                        path_str,
                        name,
                        extension,
                        artifact_type,
                        size,
                        mtime,
                        content_hash,
                        content_snippet,
                        source,
                        _utc_now(),
                        artifact_id,
                    ),
                )


            else:

                artifact_id = (
                    self._generate_artifact_id(
                        path,
                        content_hash,
                    )
                )

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

                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        'active', ?, ?, ?
                    )
                    """,
                    (
                        artifact_id,
                        path_str,
                        name,
                        extension,
                        artifact_type,
                        size,
                        mtime,
                        content_hash,
                        content_snippet,
                        source,
                        _utc_now(),
                        _utc_now(),
                    ),
                )

            self.conn.commit()

        return artifact_id


    def get(self, artifact_id):

        with self._lock:

            return self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE id = ?
                """,
                (artifact_id,),
            ).fetchone()


    def get_by_path(self, path):

        path = Path(path).resolve()

        with self._lock:

            return self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE path = ?
                """,
                (str(path),),
            ).fetchone()


    def mark_missing(self, path):

        path = Path(path).resolve()

        with self._lock:

            self.conn.execute(
                """
                UPDATE artifacts

                SET
                    status = 'missing',
                    last_seen = ?

                WHERE path = ?
                """,
                (
                    _utc_now(),
                    str(path),
                ),
            )

            self.conn.commit()


    def rename(
        self,
        old_path,
        new_path,
    ):

        old_path = Path(old_path).resolve()
        new_path = Path(new_path).resolve()

        with self._lock:

            existing = self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE path = ?
                """,
                (str(old_path),),
            ).fetchone()


            if existing is None:

                return None


            destination = self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE path = ?
                """,
                (str(new_path),),
            ).fetchone()


            if (
                destination is not None
                and destination["id"] != existing["id"]
            ):

                self.conn.execute(
                    """
                    DELETE FROM artifacts
                    WHERE path = ?
                    """,
                    (str(new_path),),
                )


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
                    _utc_now(),
                    existing["id"],
                ),
            )

            self.conn.commit()

            return existing["id"]

    def find_by_hash(self, content_hash):

        with self._lock:

            return self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE content_hash = ?
                AND status = 'active'
                """,
                (content_hash,),
            ).fetchall()

    def all_active(self):

        with self._lock:

            return self.conn.execute(
                """
                SELECT *
                FROM artifacts
                WHERE status = 'active'
                ORDER BY name
                """
            ).fetchall()


    def search_by_type(self, artifact_type):

        with self._lock:

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
                (artifact_type,),
            ).fetchall()

    def update_content_snippet(
        self,
        artifact_id,
        content_snippet,
    ):

        with self._lock:

            self.conn.execute(
                """
                UPDATE artifacts

                SET
                    content_snippet = ?,
                    last_seen = ?

                WHERE id = ?
                """,
                (
                    content_snippet,
                    _utc_now(),
                    artifact_id,
                ),
            )

            self.conn.commit()


    def has_seen_assignment(
        self,
        coursework_id,
    ):

        with self._lock:

            row = self.conn.execute(
                """
                SELECT coursework_id
                FROM seen_assignments
                WHERE coursework_id = ?
                """,
                (coursework_id,),
            ).fetchone()

            return row is not None


    def mark_assignment_seen(
        self,
        coursework_id,
        course_id,
        title,
    ):

        with self._lock:

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
                    _utc_now(),
                ),
            )

            self.conn.commit()

    def close(self):

        with self._lock:

            self.conn.close()