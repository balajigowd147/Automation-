from typing import Literal

from pydantic import BaseModel, Field


class Requirement(BaseModel):

    name: str = Field(
        description="The exact artifact or task explicitly requested."
    )

    artifact_type: Literal[
        "report",
        "certificate",
        "document",
        "image",
        "screenshot",
        "code",
        "presentation",
        "spreadsheet",
        "video",
        "audio",
        "link",
        "unknown"
    ]

    format: str = Field(
        description=(
            "The explicitly requested file format. "
            "Use 'unknown' if the assignment does not specify one."
        )
    )

    evidence: str = Field(
        description=(
            "Short exact evidence from the assignment "
            "supporting this requirement."
        )
    )


class AssignmentAnalysis(BaseModel):

    assignment_title: str

    requirements: list[Requirement]

    submission_type: Literal[
        "single_file",
        "multiple_files",
        "text",
        "link",
        "unknown"
    ]