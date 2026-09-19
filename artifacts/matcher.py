import json

from rapidfuzz import fuzz

from artifacts.registry import ArtifactRegistry
from llm.qwen_client import ask_qwen_json

def shortlist_candidates(
    requirement,
    registry: ArtifactRegistry,
    top_k=6,
):

    artifact_type = requirement.get(
        "artifact_type",
        "unknown",
    )

    if artifact_type != "unknown":
        artifacts = registry.search_by_type(
            artifact_type
        )
    else:
        artifacts = registry.all_active()

    requirement_text = " ".join(
        str(value)
        for value in [
            requirement.get("name", ""),
            requirement.get("description", ""),
            requirement.get("evidence", ""),
            requirement.get("keywords", ""),
        ]
        if value
    ).strip()

    scored = []

    for artifact in artifacts:
        candidate_text = " ".join(
            str(value)
            for value in [
                artifact["name"],
                artifact["artifact_type"],
                artifact["content_snippet"] or "",
            ]
            if value
        )

        score = fuzz.token_set_ratio(
            requirement_text,
            candidate_text,
        )

        scored.append(
            (
                score,
                artifact,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        artifact
        for _, artifact
        in scored[:top_k]
    ]

def _build_qwen_prompt(
    requirement,
    candidates,
):

    candidate_blocks = []

    for candidate in candidates:

        candidate_blocks.append(
            f"""
Artifact ID:
{candidate["id"]}

Artifact name:
{candidate["name"]}

Artifact type:
{candidate["artifact_type"]}

Artifact path:
{candidate["path"]}

Artifact content snippet:
{candidate["content_snippet"] or "[No content snippet available]"}
""".strip()
        )

    candidates_text = "\n\n".join(
        candidate_blocks
    )

    return f"""
You are selecting an existing local artifact for a
Google Classroom assignment requirement.

You MUST choose ONLY from the candidate artifacts
provided below.

You MUST NOT invent:
    - artifact IDs
    - file paths
    - filenames

If none of the candidates is appropriate, select null.

Assignment requirement:
{json.dumps(requirement, indent=2)}

Candidate artifacts:
{candidates_text}

Return ONLY a JSON object with exactly these fields:

{{
    "selected_artifact_id": "EXACT_CANDIDATE_ID_OR_NULL",
    "confidence": 0.0,
    "reason": "short explanation"
}}

Rules:

1. selected_artifact_id must be one of the provided
   candidate artifact IDs or null.

2. Never create a new artifact ID.

3. Never create a new path.

4. Do not select an artifact merely because its filename
   looks similar.

5. Consider the artifact name, type, and content snippet.

6. If there is insufficient evidence, return null.

7. confidence must be between 0.0 and 1.0.
""".strip()

def _parse_qwen_response(response_text):

    if not response_text:
        return None

    try:
        data = json.loads(
            response_text
        )
    except json.JSONDecodeError as error:

        print(
            "[matcher] Qwen returned invalid JSON: "
            f"{error}"
        )

        return None

    if not isinstance(data, dict):

        print(
            "[matcher] Qwen JSON response is not "
            "an object."
        )

        return None

    if "selected_artifact_id" not in data:

        print(
            "[matcher] Qwen response is missing "
            "selected_artifact_id."
        )

        return None

    selected_id = data.get(
        "selected_artifact_id"
    )

    if selected_id in (
        None,
        "",
        "null",
        "None",
    ):

        selected_id = None

    data["selected_artifact_id"] = selected_id

    confidence = data.get(
        "confidence",
        0.0,
    )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ):

        confidence = 0.0

    confidence = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )

    data["confidence"] = confidence

    reason = data.get(
        "reason",
        "",
    )

    if reason is None:

        reason = ""

    data["reason"] = str(
        reason
    )

    return data

def rerank_with_qwen(
    requirement,
    candidates,
):

    if not candidates:

        print(
            "[matcher] No candidates available "
            "for Qwen reranking."
        )

        return None

    prompt = _build_qwen_prompt(
        requirement,
        candidates,
    )

    try:

        response_text = ask_qwen_json(
            prompt,
            temperature=0.0,
        )

    except Exception as error:

        print(
            "[matcher] Qwen request failed: "
            f"{error}"
        )
        return None

    print(
        "\n[matcher] Qwen response:"
    )

    print(
        response_text
    )

    result = _parse_qwen_response(
        response_text
    )

    if result is None:
        return None

    selected_id = result[
        "selected_artifact_id"
    ]

    if selected_id is None:
        print("[matcher] Qwen found no suitable artifact.")
        return None

    candidate_ids = {
        candidate["id"]
        for candidate in candidates
    }

    if selected_id not in candidate_ids:

        print(
            "[matcher] Qwen returned an invalid "
            "artifact ID."
        )

        print(
            f"[matcher] Invalid ID: {selected_id}"
        )

        print(
            "[matcher] Treating this as no match."
        )

        return None

    selected_artifact = next(
        (
            candidate
            for candidate in candidates
            if candidate["id"] == selected_id
        ),
        None,
    )


    if selected_artifact is None:

        print(
            "[matcher] Selected artifact could not "
            "be resolved from candidates."
        )

        return None

    return {
        "artifact": selected_artifact,
        "confidence": result[
            "confidence"
        ],
        "reason": result[
            "reason"
        ],
    }

def match_artifact(
    requirement,
    registry: ArtifactRegistry,
    top_k=6,
):

    candidates = shortlist_candidates(
        requirement,
        registry,
        top_k=top_k,
    )

    print(
        f"[matcher] Shortlisted "
        f"{len(candidates)} candidate(s)."
    )

    for candidate in candidates:

        print(
            f"    - {candidate['id']} | "
            f"{candidate['name']} | "
            f"{candidate['artifact_type']}"
        )

    result = rerank_with_qwen(
        requirement,
        candidates,
    )

    if result is None:

        print(
            "[matcher] No validated artifact match."
        )

        return None

    artifact = result[
        "artifact"
    ]

    print(
        "\n[matcher] Artifact selected:"
    )

    print(
        f"    ID: {artifact['id']}"
    )

    print(
        f"    Name: {artifact['name']}"
    )

    print(
        f"    Type: {artifact['artifact_type']}"
    )

    print(
        f"    Path: {artifact['path']}"
    )

    print(
        f"    Confidence: "
        f"{result['confidence']:.2f}"
    )

    print(
        f"    Reason: "
        f"{result['reason']}"
    )

    return result