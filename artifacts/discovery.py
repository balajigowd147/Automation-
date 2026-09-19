from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from artifacts.registry import ArtifactRegistry
import os

DEFAULT_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".pptx",
    ".xlsx",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "datasets",
    "dataset",
    "data",
    "cache",
    "caches",
    "tmp",
    "temp",
}


def guess_artifact_type(name: str) -> str:

    lowered = name.lower()

    if "certificate" in lowered or "cert" in lowered:
        return "certificate"

    if "report" in lowered:
        return "report"

    if "resume" in lowered or "cv" in lowered:
        return "resume"

    return "unknown"


def iter_supported_files(root, extensions, excluded_dirs=None):

    root = Path(root)

    if excluded_dirs is None:
        excluded_dirs = EXCLUDED_DIR_NAMES

    excluded = {
        name.lower()
        for name in excluded_dirs
    }

    for current_root, dir_names, file_names in os.walk(root):

        dir_names[:] = [
            name
            for name in dir_names
            if name.lower() not in excluded
        ]

        current_path = Path(current_root)

        for file_name in file_names:
            path = current_path / file_name

            if path.suffix.lower() in extensions:
                yield path

def initial_scan(
    registry: ArtifactRegistry,
    root_dirs,
    extensions=DEFAULT_EXTENSIONS,
):
    count = 0

    for root in root_dirs:

        root_path = Path(root)

        if not root_path.exists():
            print(
                f"[discovery] Root does not exist: {root_path}"
            )
            continue

        print(
            f"[discovery] Scanning: {root_path}"
        )

        for path in iter_supported_files(
            root_path,
            extensions,
        ):

            artifact_type = guess_artifact_type(
                path.name
            )

            registry.register(
                str(path),
                artifact_type=artifact_type,
            )

            count += 1

            print(
                f"[discovery] Registered: "
                f"{path.name} -> {artifact_type}"
            )

    print(
        f"\n[discovery] Initial scan complete. "
        f"Registered/updated {count} files."
    )

def reconcile(registry: ArtifactRegistry):


    print("\n[discovery] Starting reconciliation...")
    active_artifacts = registry.all_active()

    missing_candidates = []

    for artifact in active_artifacts:

        path = Path(artifact["path"])

        if not path.exists():

            print(
                f"[discovery] Missing file detected: "
                f"{path}"
            )

            missing_candidates.append(artifact)

            continue

        try:
            stat = path.stat()

        except OSError as error:

            print(
                f"[discovery] Could not inspect "
                f"{path}: {error}"
            )

            continue

        if (
            stat.st_mtime != artifact["mtime"]
            or stat.st_size != artifact["size"]
        ):

            print(
                f"[discovery] File changed: "
                f"{path}"
            )
            registry.register(
                path,
                artifact_type=artifact["artifact_type"],
                source=artifact["source"],
            )

    for artifact in missing_candidates:

        old_path = Path(artifact["path"])
        matches = registry.find_by_hash(
            artifact["content_hash"]
        )

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

class RegistryEventHandler(FileSystemEventHandler):

    def __init__(
        self,
        registry: ArtifactRegistry,
        extensions=DEFAULT_EXTENSIONS,
    ):
        super().__init__()

        self.registry = registry
        self.extensions = extensions

    def _relevant(self, path_str):
        """
        Return True if the file has a supported extension.
        """

        return (
            Path(path_str).suffix.lower()
            in self.extensions
        )

    def on_created(self, event): 

        if event.is_directory:
            return

        if not self._relevant(event.src_path):
            return

        path = Path(event.src_path)
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

        row = self.registry.get_by_path(path)

        artifact_type = (
            row["artifact_type"]
            if row
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

    def on_moved(self, event):

        if event.is_directory:
            return

        old_relevant = self._relevant(
            event.src_path
        )

        new_relevant = self._relevant(
            event.dest_path
        )
        if not old_relevant and not new_relevant:
            return

        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)

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

def start_watcher(
    registry: ArtifactRegistry,
    root_dirs,
):

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


def register_agent_file(
    registry: ArtifactRegistry,
    path,
    artifact_type="unknown",
    downloaded=False,
):

    path = Path(path)

    if not path.exists() or not path.is_file():
        print(
            f"[discovery] Agent file does not exist: "
            f"{path}"
        )

        return None

    source = (
        "agent_downloaded"
        if downloaded
        else "agent_created"
    )

    if artifact_type == "unknown":
        artifact_type = guess_artifact_type(
            path.name
        )

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