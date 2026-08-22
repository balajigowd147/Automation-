"""
Artifact File Reader

Reads the actual contents of files registered in the
Artifact Registry.

Supported formats:
    .txt
    .pdf
    .docx

The reader does NOT move or copy files.

It receives the real path stored in the registry,
opens that file, and extracts text from it.
"""

from pathlib import Path

from pypdf import PdfReader
from docx import Document


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_MAX_CHARS = 5000


# ---------------------------------------------------------
# TXT reader
# ---------------------------------------------------------

def read_txt(path: Path) -> str:
    """
    Read a plain text file.
    """

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


# ---------------------------------------------------------
# PDF reader
# ---------------------------------------------------------

def read_pdf(path: Path) -> str:
    """
    Extract text from a PDF file.
    """

    reader = PdfReader(str(path))

    pages = []

    for page in reader.pages:

        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)


# ---------------------------------------------------------
# DOCX reader
# ---------------------------------------------------------

def read_docx(path: Path) -> str:
    """
    Extract text from a DOCX document.
    """

    document = Document(str(path))

    paragraphs = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


# ---------------------------------------------------------
# Generic file reader
# ---------------------------------------------------------

def read_file(
    path,
    max_chars=DEFAULT_MAX_CHARS,
) -> str:
    """
    Read a supported file and return extracted text.

    Parameters
    ----------
    path:
        Real filesystem path.

    max_chars:
        Maximum amount of text returned.

    Returns
    -------
    str
        Extracted text.

    Raises
    ------
    FileNotFoundError
        If the file doesn't exist.

    ValueError
        If the file format isn't supported.
    """

    path = Path(path).resolve()

    # -----------------------------------------------------
    # Validate file
    # -----------------------------------------------------

    if not path.exists():

        raise FileNotFoundError(
            f"Artifact does not exist: {path}"
        )

    if not path.is_file():

        raise ValueError(
            f"Path is not a file: {path}"
        )

    extension = path.suffix.lower()

    # -----------------------------------------------------
    # Select reader
    # -----------------------------------------------------

    if extension == ".txt":

        text = read_txt(path)

    elif extension == ".pdf":

        text = read_pdf(path)

    elif extension == ".docx":

        text = read_docx(path)

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    # -----------------------------------------------------
    # Normalize text
    # -----------------------------------------------------

    text = text.strip()

    # -----------------------------------------------------
    # Limit returned content
    # -----------------------------------------------------

    if max_chars is not None:

        text = text[:max_chars]

    return text


# ---------------------------------------------------------
# Read using an Artifact Registry record
# ---------------------------------------------------------

def read_artifact(
    registry,
    artifact_id,
    max_chars=DEFAULT_MAX_CHARS,
):
    """
    Read an artifact using its registry ID.

    Flow:

        artifact_id
             ↓
        registry.get()
             ↓
        real file path
             ↓
        read_file()
             ↓
        extracted text
    """

    artifact = registry.get(
        artifact_id
    )

    if artifact is None:

        raise ValueError(
            f"Artifact not found in registry: "
            f"{artifact_id}"
        )

    # -----------------------------------------------------
    # Make sure registry doesn't point to a missing file
    # -----------------------------------------------------

    if artifact["status"] != "active":

        raise FileNotFoundError(
            f"Artifact is not active: "
            f"{artifact['path']}"
        )

    # -----------------------------------------------------
    # Read the actual file
    # -----------------------------------------------------

    return read_file(
        artifact["path"],
        max_chars=max_chars,
    )



# ---------------------------------------------------------
# Update registry with extracted content
# ---------------------------------------------------------

def update_artifact_snippet(
    registry,
    artifact_id,
    max_chars=1000,
):
    """
    Read an artifact and store a short content snippet
    in the Artifact Registry.

    Flow:

        artifact_id
             ↓
        registry.get()
             ↓
        real file path
             ↓
        read_file()
             ↓
        extracted text
             ↓
        content_snippet
             ↓
        SQLite
    """

    artifact = registry.get(artifact_id)

    if artifact is None:
        raise ValueError(
            f"Artifact not found: {artifact_id}"
        )

    text = read_file(
        artifact["path"],
        max_chars=max_chars,
    )

    # -----------------------------------------------------
    # Store extracted snippet
    # -----------------------------------------------------

    registry.conn.execute(
        """
        UPDATE artifacts
        SET
            content_snippet = ?,
            last_seen = ?
        WHERE id = ?
        """,
        (
            text,
            artifact["last_seen"],
            artifact_id,
        ),
    )

    registry.conn.commit()

    return text