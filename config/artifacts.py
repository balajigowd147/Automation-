from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOCUMENTS_ROOT = Path(os.environ["OneDrive"]) / "Documents"

ARTIFACT_ROOTS = [
    DOCUMENTS_ROOT / "Certificates",
    DOCUMENTS_ROOT / "Reports",
    DOCUMENTS_ROOT / "Resumes",
    DOCUMENTS_ROOT / "Presentations",
]

ARTIFACT_DB = PROJECT_ROOT / "data" / "artifacts.db"