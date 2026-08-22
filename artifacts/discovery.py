"""
Artifact discovery system.

Part 1:
    Initial filesystem scan.

This module finds existing files in configured directories
and registers them in the Artifact Registry.
"""

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from artifacts.registry import ArtifactRegistry


# ---------------------------------------------------------
# Supported artifact extensions
# ---------------------------------------------------------

DEFAULT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".pptx",
    ".xlsx",
    ".zip",
}


# ---------------------------------------------------------
# Artifact type detection
# ---------------------------------------------------------

def guess_artifact_type(name: str) -> str:
    """
    Guess the artifact type from the filename.

    This is intentionally a simple heuristic.

    The matcher/LLM will perform more intelligent
    matching later.
    """

    lowered = name.lower()

    if "certificate" in lowered or "cert" in lowered:
        return "certificate"

    if "report" in lowered:
        return "report"

    if "resume" in lowered or "cv" in lowered:
        return "resume"

    return "unknown"


# ---------------------------------------------------------
# Initial filesystem scan
# ---------------------------------------------------------

def initial_scan(
    registry: ArtifactRegistry,
    root_dirs,
    extensions=DEFAULT_EXTENSIONS,
):
    """
    Scan the configured directories recursively.

    Every supported file found is registered in SQLite.

    Parameters
    ----------
    registry:
        ArtifactRegistry instance.

    root_dirs:
        List of directories to scan.

    extensions:
        File extensions that should be registered.

    Returns
    -------
    int
        Number of files discovered.
    """

    count = 0

    for root in root_dirs:

        root_path = Path(root)

        # Skip directories that don't exist.
        if not root_path.exists():
            print(
                f"[discovery] Directory does not exist: "
                f"{root_path}"
            )
            continue

        if not root_path.is_dir():
            print(
                f"[discovery] Not a directory: "
                f"{root_path}"
            )
            continue

        print(
            f"[discovery] Scanning: "
            f"{root_path.resolve()}"
        )

        # Recursively walk through the directory.
        for path in root_path.rglob("*"):

            # Ignore directories.
            if not path.is_file():
                continue

            # Only process supported extensions.
            if path.suffix.lower() not in extensions:
                continue

            artifact_type = guess_artifact_type(
                path.name
            )

            artifact_id = registry.register(
                path,
                artifact_type=artifact_type,
                source="discovered",
            )

            if artifact_id:
                count += 1

                print(
                    f"[discovery] Registered: "
                    f"{path.name} "
                    f"-> {artifact_type} "
                    f"({artifact_id})"
                )

    print(
        f"\n[discovery] Initial scan complete."
        f" Registered/updated {count} files."
    )

    return count


# ---------------------------------------------------------
# Startup reconciliation
# ---------------------------------------------------------

def reconcile(registry: ArtifactRegistry):
    """
    Reconcile the SQLite registry with the actual filesystem.

    This is executed when the agent starts.

    It detects:

    1. Files that were deleted while the agent was OFF.
    2. Files that were modified while the agent was OFF.
    3. Files whose size/mtime changed.
    4. Files that may have been moved and later discovered
       under another path.

    The registry is updated accordingly.
    """

    print("\n[discovery] Starting reconciliation...")

    # Get all artifacts that the registry currently considers active.
    active_artifacts = registry.all_active()

    missing_candidates = []

    # -----------------------------------------------------
    # Check every registered artifact
    # -----------------------------------------------------

    for artifact in active_artifacts:

        path = Path(artifact["path"])

        # -------------------------------------------------
        # File no longer exists
        # -------------------------------------------------

        if not path.exists():

            print(
                f"[discovery] Missing file detected: "
                f"{path}"
            )

            missing_candidates.append(artifact)

            continue

        # -------------------------------------------------
        # File still exists
        # -------------------------------------------------

        try:
            stat = path.stat()

        except OSError as error:

            print(
                f"[discovery] Could not inspect "
                f"{path}: {error}"
            )

            continue

        # -------------------------------------------------
        # Detect modification
        # -------------------------------------------------

        if (
            stat.st_mtime != artifact["mtime"]
            or stat.st_size != artifact["size"]
        ):

            print(
                f"[discovery] File changed: "
                f"{path}"
            )

            # Re-registering causes the registry to
            # recalculate the quick fingerprint.
            registry.register(
                path,
                artifact_type=artifact["artifact_type"],
                source=artifact["source"],
            )

    # -----------------------------------------------------
    # Handle files that disappeared
    # -----------------------------------------------------

    for artifact in missing_candidates:

        old_path = Path(artifact["path"])

        # Try to find an active artifact with the same
        # quick content fingerprint.
        matches = registry.find_by_hash(
            artifact["content_hash"]
        )

        # Only consider a different path as a possible move.
        moved_candidates = [
            match
            for match in matches
            if match["path"] != artifact["path"]
        ]

        if moved_candidates:

            new_artifact = moved_candidates[0]

            print(
                f"[discovery] Possible move detected:"
                f"\n    Old: {old_path}"
                f"\n    New: {new_artifact['path']}"
            )

            # The new path is already registered.
            # Keep the old database row for history,
            # but mark it as missing.
            registry.mark_missing(old_path)

        else:

            print(
                f"[discovery] File no longer exists:"
                f" {old_path}"
            )

            registry.mark_missing(old_path)

    print(
        "[discovery] Reconciliation complete."
    )



# ---------------------------------------------------------
# Real-time filesystem watcher
# ---------------------------------------------------------

class RegistryEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events and keeps the Artifact Registry
    synchronized in real time.
    """

    def __init__(
        self,
        registry: ArtifactRegistry,
        extensions=DEFAULT_EXTENSIONS,
    ):
        super().__init__()

        self.registry = registry
        self.extensions = extensions

    # -----------------------------------------------------
    # Check whether a file is relevant
    # -----------------------------------------------------

    def _relevant(self, path_str):
        """
        Return True if the file has a supported extension.
        """

        return (
            Path(path_str).suffix.lower()
            in self.extensions
        )

    # -----------------------------------------------------
    # File created
    # -----------------------------------------------------

    def on_created(self, event):
        """
        Called when a new file is created.
        """

        if event.is_directory:
            return

        if not self._relevant(event.src_path):
            return

        path = Path(event.src_path)

        # A file may be created before its contents are
        # completely written. We therefore make sure it
        # exists before attempting registration.
        if not path.exists():
            return

        artifact_type = guess_artifact_type(
            path.name
        )

        artifact_id = self.registry.register(
            path,
            artifact_type=artifact_type,
            source="discovered",
        )

        if artifact_id:
            print(
                f"[watcher] New file registered: "
                f"{path} "
                f"({artifact_id})"
            )

    # -----------------------------------------------------
    # File modified
    # -----------------------------------------------------

    def on_modified(self, event):
        """
        Called when an existing file is modified.
        """

        if event.is_directory:
            return

        if not self._relevant(event.src_path):
            return

        path = Path(event.src_path)

        if not path.exists():
            return

        existing = self.registry.conn.execute(
    """
    SELECT artifact_type
    FROM artifacts
    WHERE path = ?
    """,
    (str(path.resolve()),)).fetchone()

        artifact_type = (
            existing["artifact_type"]
            if existing
            else guess_artifact_type(path.name)
        )

        artifact_id = self.registry.register(
            path,
            artifact_type=artifact_type,
            source="discovered",
        )

        if artifact_id:
            print(
                f"[watcher] File updated: "
                f"{path} "
                f"({artifact_id})"
            )

    # -----------------------------------------------------
    # File deleted
    # -----------------------------------------------------

    def on_deleted(self, event):
        """
        Called when a registered file is deleted.
        """

        if event.is_directory:
            return

        if not self._relevant(event.src_path):
            return

        self.registry.mark_missing(
            event.src_path
        )

        print(
            f"[watcher] File marked missing: "
            f"{event.src_path}"
        )

    # -----------------------------------------------------
    # File moved / renamed
    # -----------------------------------------------------

    def on_moved(self, event):
        """
        Called when a file is moved or renamed.

        The registry keeps the same artifact ID.
        """

        # We only care about files.
        if event.is_directory:
            return

        old_relevant = self._relevant(
            event.src_path
        )

        new_relevant = self._relevant(
            event.dest_path
        )

        # If neither side is a supported artifact,
        # ignore the event.
        if not old_relevant and not new_relevant:
            return

        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)

        # -------------------------------------------------
        # Supported → Supported
        # -------------------------------------------------

        if old_relevant and new_relevant:

            self.registry.rename(
                old_path,
                new_path
            )

            print(
                f"[watcher] File moved: "
                f"{old_path} -> {new_path}"
            )

            return

        # -------------------------------------------------
        # Supported → Unsupported
        # -------------------------------------------------

        if old_relevant and not new_relevant:

            self.registry.mark_missing(
                old_path
            )

            print(
                f"[watcher] Artifact moved outside "
                f"supported extensions: "
                f"{old_path} -> {new_path}"
            )

            return

        # -------------------------------------------------
        # Unsupported → Supported
        # -------------------------------------------------

        if not old_relevant and new_relevant:

            if new_path.exists():

                artifact_type = guess_artifact_type(
                    new_path.name
                )

                artifact_id = self.registry.register(
                    new_path,
                    artifact_type=artifact_type,
                    source="discovered",
                )

                print(
                    f"[watcher] File became an artifact: "
                    f"{new_path} "
                    f"({artifact_id})"
                )


# ---------------------------------------------------------
# Start filesystem watcher
# ---------------------------------------------------------

def start_watcher(
    registry: ArtifactRegistry,
    root_dirs,
):
    """
    Start the filesystem watcher.

    The watcher runs in the background.

    Returns
    -------
    Observer
        The watchdog observer instance.

    The caller is responsible for stopping it.
    """

    handler = RegistryEventHandler(
        registry
    )

    observer = Observer()

    watched_count = 0

    for root in root_dirs:

        root_path = Path(root)

        if not root_path.exists():
            print(
                f"[watcher] Directory does not exist: "
                f"{root_path}"
            )
            continue

        if not root_path.is_dir():
            print(
                f"[watcher] Not a directory: "
                f"{root_path}"
            )
            continue

        observer.schedule(
            handler,
            str(root_path),
            recursive=True,
        )

        watched_count += 1

    if watched_count == 0:
        print(
            "[watcher] No valid directories to watch."
        )
        return observer

    observer.start()

    print(
        f"[watcher] Watching "
        f"{watched_count} director"
        f"{'y' if watched_count == 1 else 'ies'} "
        f"in real time."
    )

    return observer

# ---------------------------------------------------------
# Register files created/downloaded by the agent
# ---------------------------------------------------------

def register_agent_file(
    registry: ArtifactRegistry,
    path,
    artifact_type="unknown",
    downloaded=False,
):
    """
    Immediately register a file created or downloaded
    by the agent.

    Parameters
    ----------
    registry:
        ArtifactRegistry instance.

    path:
        Path of the created/downloaded file.

    artifact_type:
        Known artifact type if available.

    downloaded:
        True  -> agent_downloaded
        False -> agent_created

    Returns
    -------
    str | None
        Artifact ID if registration succeeds.
    """

    path = Path(path)

    # -----------------------------------------------------
    # Make sure the file actually exists
    # -----------------------------------------------------

    if not path.exists() or not path.is_file():
        print(
            f"[discovery] Agent file does not exist: "
            f"{path}"
        )

        return None

    # -----------------------------------------------------
    # Determine source
    # -----------------------------------------------------

    source = (
        "agent_downloaded"
        if downloaded
        else "agent_created"
    )

    # -----------------------------------------------------
    # If type wasn't explicitly supplied, infer it
    # -----------------------------------------------------

    if artifact_type == "unknown":
        artifact_type = guess_artifact_type(
            path.name
        )

    # -----------------------------------------------------
    # Register immediately
    # -----------------------------------------------------

    artifact_id = registry.register(
        path,
        artifact_type=artifact_type,
        source=source,
    )

    print(
        f"[discovery] Agent-produced file registered: "
        f"{path}"
        f"\n    Source: {source}"
        f"\n    Type: {artifact_type}"
        f"\n    ID: {artifact_id}"
    )

    return artifact_id