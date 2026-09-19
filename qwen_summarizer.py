import requests


QWEN_MODEL = "qwen3:latest"
OLLAMA_URL = "http://localhost:11434/api/chat"

CHUNK_SIZE = 5000


def ask_qwen(prompt):
    """
    Send a prompt to Qwen through Ollama.
    """

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": QWEN_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        },
        timeout=120,
    )

    if response.status_code != 200:
        print("\n========== OLLAMA ERROR ==========")
        print("Status:", response.status_code)
        print("Response:", response.text)
        print("==================================\n")

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


def summarize_text(text):
    """
    Summarize a relatively small piece of study material.
    """

    prompt = f"""
You are a helpful study assistant.

Summarize the following study material clearly.

Give:
1. Main topic
2. Important concepts
3. Key points
4. A short overall summary

Study material:

{text}
"""

    return ask_qwen(prompt)


def split_text(text, chunk_size=CHUNK_SIZE):
    """
    Split a large document into manageable chunks.

    Tries to split at paragraph boundaries where possible.
    """

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        if end < text_length:

            paragraph_break = text.rfind(
                "\n",
                start,
                end,
            )

            if paragraph_break > start:
                end = paragraph_break

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end

    return chunks


def summarize_document(text):
    """
    Summarize a large document using hierarchical summarization.

    Large documents are first split into chunks.
    Each chunk is summarized independently.
    The chunk summaries are then combined in small groups.
    Finally, Qwen creates one coherent overall summary.
    """
    if not text or not text.strip():
        return ""

    chunks = split_text(text)

    print(f"\nDocument length: {len(text)} characters")
    print(f"Created {len(chunks)} chunks")

    # ---------------------------------------------------------
    # STEP 1: Summarize each document chunk
    # ---------------------------------------------------------

    if len(chunks) == 1:
        print("\nSmall document → direct Qwen summary")
        return summarize_text(chunks[0])

    chunk_summaries = []

    for index, chunk in enumerate(chunks, start=1):
        print(
            f"\nSummarizing chunk "
            f"{index}/{len(chunks)} "
            f"({len(chunk)} characters)..."
        )

        summary = summarize_text(chunk)
        chunk_summaries.append(summary)

    print("\nAll chunks summarized.")
    print(
        f"Number of chunk summaries: "
        f"{len(chunk_summaries)}"
    )

    # ---------------------------------------------------------
    # STEP 2: Combine chunk summaries in small groups
    # ---------------------------------------------------------

    GROUP_SIZE = 3
    group_summaries = []

    for start in range(0, len(chunk_summaries), GROUP_SIZE):

        group = chunk_summaries[
            start:start + GROUP_SIZE
        ]

        group_text = "\n\n".join(group)

        group_number = (
            start // GROUP_SIZE
        ) + 1

        total_groups = (
            len(chunk_summaries) + GROUP_SIZE - 1
        ) // GROUP_SIZE

        print(
            f"\nCombining summary group "
            f"{group_number}/{total_groups}..."
        )

        group_prompt = f"""
You are a helpful study assistant.

The following are summaries of nearby sections
of the same study material.

Combine them into one concise and accurate
section summary.

Preserve important:
- concepts
- definitions
- explanations
- examples
- terminology

Do not add information that is not supported
by the provided summaries.

Section summaries:

{group_text}
"""

        group_summary = ask_qwen(group_prompt)

        group_summaries.append(group_summary)

    print("\nAll summary groups combined.")

    # ---------------------------------------------------------
    # STEP 3: Create the final overall summary
    # ---------------------------------------------------------

    final_text = "\n\n".join(group_summaries)

    print(
        f"Final synthesis input length: "
        f"{len(final_text)} characters"
    )

    final_prompt = f"""
You are a helpful study assistant.

Create one coherent final study summary from
the section summaries below.

Give:

1. Main topic
2. Important concepts
3. Key definitions and explanations
4. Important examples or applications
5. Key points to remember
6. Short overall summary

Requirements:

- Keep the information accurate.
- Preserve the terminology from the material.
- Do not invent information.
- Do not mention chunking, groups, or this
  summarization process.
- Remove unnecessary repetition.

Section summaries:

{final_text}
"""

    print("\nCreating final overall summary...")

    return ask_qwen(final_prompt)