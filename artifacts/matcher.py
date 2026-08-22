"""
Artifact Matcher

Stage 1:
    Python candidate filtering and ranking.

Stage 2:
    Local Qwen semantic reranking through Ollama.

The LLM is never allowed to invent artifact IDs or paths.
Python validates the returned artifact ID.
"""

import json
import re

from rapidfuzz import fuzz
from ollama import chat

from artifacts.registry import ArtifactRegistry
from artifacts.file_reader import read_artifact


# ---------------------------------------------------------
# Stage 1 — Python candidate shortlist
# ---------------------------------------------------------

def shortlist_candidates(
    requirement,
    registry: ArtifactRegistry,
    top_k=6,
):
    """
    Produce a small candidate set using deterministic
    Python filtering and filename similarity.
    """

    artifact_type = requirement.get(
        "artifact_type",
        "unknown",
    )

    # Filter by artifact type first.
    if artifact_type != "unknown":
        pool = registry.search_by_type(
            artifact_type
        )
    else:
        pool = registry.all_active()

    query_text = (
        f"{requirement.get('name', '')} "
        f"{requirement.get('evidence', '')}"
    ).strip()

    scored = []

    for artifact in pool:

        score = fuzz.token_set_ratio(
            query_text.lower(),
            artifact["name"].lower(),
        )

        scored.append(
            (score, artifact)
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        artifact
        for score, artifact in scored[:top_k]
    ]


# ---------------------------------------------------------
# Stage 2 — Build Qwen candidate prompt
# ---------------------------------------------------------

def _build_qwen_prompt(
    requirement,
    candidates,
):
    """
    Build a strict prompt containing only real candidate IDs.
    """

    candidate_text = []

    for artifact in candidates:

        candidate_text.append(
            f"""
ARTIFACT ID: {artifact['id']}
NAME: {artifact['name']}
TYPE: {artifact['artifact_type']}
PATH: {artifact['path']}
CONTENT:
{artifact['content_snippet'] or '[No snippet available]'}
""".strip()
        )

    candidates_block = "\n\n".join(
        candidate_text
    )

    return f"""
You are an artifact matching assistant.

Your task is to select the artifact that best satisfies
the assignment requirement.

ASSIGNMENT REQUIREMENT
----------------------
Name:
{requirement.get('name', '')}

Evidence:
{requirement.get('evidence', '')}

Artifact type:
{requirement.get('artifact_type', 'unknown')}

CANDIDATE ARTIFACTS
-------------------
{candidates_block}

IMPORTANT RULES
---------------
1. Select ONLY one artifact ID from the candidates above.
2. NEVER invent an artifact ID.
3. NEVER invent a file path.
4. Base your decision on the artifact name, type, and content.
5. If none of the candidates satisfies the requirement,
   return null.
6. Return ONLY valid JSON.

Required JSON format:

{{
    "selected_artifact_id": "EXACT_CANDIDATE_ID_OR_NULL",
    "confidence": 0.0,
    "reason": "short explanation"
}}
""".strip()


# ---------------------------------------------------------
# Parse Qwen JSON
# ---------------------------------------------------------

def _parse_qwen_response(response_text):
    """
    Extract JSON from Qwen's response.

    Handles both clean JSON and JSON surrounded by
    markdown fences.
    """

    text = response_text.strip()

    # Remove markdown code fences if Qwen adds them.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    # Find the JSON object.
    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL,
    )

    if not match:
        raise ValueError(
            "Qwen did not return a JSON object."
        )

    return json.loads(
        match.group(0)
    )


# ---------------------------------------------------------
# Qwen semantic reranking
# ---------------------------------------------------------

def rerank_with_qwen(
    requirement,
    candidates,
    model="qwen3:latest",
):
    """
    Ask local Qwen to semantically select the best
    artifact from the candidate set.

    Returns the validated artifact row or None.
    """

    if not candidates:
        return None

    candidate_ids = {
        artifact["id"]
        for artifact in candidates
    }

    prompt = _build_qwen_prompt(
        requirement,
        candidates,
    )

    print(
        "\n[matcher] Sending candidates to Qwen..."
    )

    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    response_text = response["message"]["content"]

    print(
        "\n[matcher] Qwen response:"
    )

    print(response_text)

    # -----------------------------------------------------
    # Parse response
    # -----------------------------------------------------

    result = _parse_qwen_response(
        response_text
    )

    selected_id = result.get(
        "selected_artifact_id"
    )

    # -----------------------------------------------------
    # Hard validation
    # -----------------------------------------------------

    if selected_id is None:
        print(
            "[matcher] Qwen selected no artifact."
        )

        return None

    if selected_id not in candidate_ids:

        raise ValueError(
            "Qwen returned an artifact ID that was "
            "not present in the candidate set: "
            f"{selected_id}"
        )

    # -----------------------------------------------------
    # Return the actual Python artifact object
    # -----------------------------------------------------

    selected_artifact = next(
        artifact
        for artifact in candidates
        if artifact["id"] == selected_id
    )

    return {
        "artifact": selected_artifact,
        "confidence": result.get(
            "confidence",
            0.0,
        ),
        "reason": result.get(
            "reason",
            "",
        ),
    }


# ---------------------------------------------------------
# Complete matching pipeline
# ---------------------------------------------------------

def match_artifact(
    requirement,
    registry: ArtifactRegistry,
    top_k=6,
    model="qwen3:latest",
):
    """
    Complete artifact matching pipeline.

    1. Python creates candidates.
    2. Qwen semantically reranks them.
    3. Python validates the returned ID.
    """

    print(
        "\n[matcher] Creating candidate shortlist..."
    )

    candidates = shortlist_candidates(
        requirement,
        registry,
        top_k=top_k,
    )

    print(
        f"[matcher] Candidates found: "
        f"{len(candidates)}"
    )

    if not candidates:
        return None

    # -----------------------------------------------------
    # Send candidate information to Qwen
    # -----------------------------------------------------

    result = rerank_with_qwen(
        requirement,
        candidates,
        model=model,
    )

    return result 