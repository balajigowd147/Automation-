"""
Shared Qwen3 client.

All local Qwen/Ollama calls in the project should go
through this module.

Responsibilities:
    - Qwen model configuration
    - Ollama connection
    - Retry handling
    - Thinking-mode control
    - Context-window configuration
    - Normal text generation
    - Structured JSON generation
"""


import time

from ollama import Client


# ---------------------------------------------------------
# Qwen configuration
# ---------------------------------------------------------

QWEN_MODEL = "qwen3:latest"

OLLAMA_HOST = "http://localhost:11434"

QWEN_NUM_CTX = 8192

QWEN_TIMEOUT = 180

MAX_RETRIES = 3

RETRY_DELAY = 2

KEEP_ALIVE = "10m"


# ---------------------------------------------------------
# Ollama client
# ---------------------------------------------------------

client = Client(
    host=OLLAMA_HOST,
    timeout=QWEN_TIMEOUT,
)


# ---------------------------------------------------------
# Internal Qwen call
# ---------------------------------------------------------

def _call_qwen(
    messages,
    *,
    response_format=None,
    temperature=0.2,
):
    """
    Make a single request to Qwen through Ollama.

    Parameters
    ----------
    messages:
        Ollama chat messages.

    response_format:
        None for normal text.
        "json" or a JSON schema for structured output.

    temperature:
        Sampling temperature.
    """

    return client.chat(
        model=QWEN_MODEL,
        messages=messages,

        # -------------------------------------------------
        # IMPORTANT:
        # Disable Qwen thinking for our application calls.
        #
        # This makes structured JSON responses much easier
        # to handle and avoids parsing <think> content.
        # -------------------------------------------------

        think=False,

        # -------------------------------------------------
        # Structured output when requested.
        # -------------------------------------------------

        format=response_format,

        # -------------------------------------------------
        # Ollama model options.
        # -------------------------------------------------

        options={
            "temperature": temperature,
            "num_ctx": QWEN_NUM_CTX,
        },

        # -------------------------------------------------
        # Keep model loaded for a short period so repeated
        # calls don't constantly reload it.
        # -------------------------------------------------

        keep_alive=KEEP_ALIVE,
    )


# ---------------------------------------------------------
# Normal text generation
# ---------------------------------------------------------

def ask_qwen(
    prompt,
    *,
    system=None,
    temperature=0.2,
):
    """
    Ask Qwen for a normal text response.

    Returns
    -------
    str
        Qwen's generated response.
    """

    messages = []

    # -----------------------------------------------------
    # Optional system message.
    # -----------------------------------------------------

    if system:

        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

    # -----------------------------------------------------
    # User prompt.
    # -----------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    last_error = None

    # -----------------------------------------------------
    # Retry loop.
    # -----------------------------------------------------

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = _call_qwen(
                messages,
                temperature=temperature,
            )

            # -------------------------------------------------
            # Ollama response structure:
            #
            # response["message"]["content"]
            # -------------------------------------------------

            content = response["message"][
                "content"
            ]

            return content

        except Exception as error:

            last_error = error

            print(
                "[qwen] Request failed "
                f"(attempt {attempt}/"
                f"{MAX_RETRIES}): "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

    # -----------------------------------------------------
    # All retries failed.
    # -----------------------------------------------------

    raise RuntimeError(
        "Qwen request failed after "
        f"{MAX_RETRIES} attempts."
    ) from last_error


# ---------------------------------------------------------
# Structured JSON generation
# ---------------------------------------------------------

def ask_qwen_json(
    prompt,
    *,
    schema=None,
    system=None,
    temperature=0.0,
):
    """
    Ask Qwen for a structured JSON response.

    Parameters
    ----------
    prompt:
        User prompt.

    schema:
        Optional JSON schema.

        If omitted, Ollama's generic JSON mode
        is used.

    system:
        Optional system message.

    temperature:
        Sampling temperature.

    Returns
    -------
    str
        JSON response as a string.
    """

    messages = []

    # -----------------------------------------------------
    # Optional system message.
    # -----------------------------------------------------

    if system:

        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )

    # -----------------------------------------------------
    # User prompt.
    # -----------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    last_error = None

    # -----------------------------------------------------
    # Retry loop.
    # -----------------------------------------------------

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = _call_qwen(
                messages,
                response_format=(
                    schema
                    if schema is not None
                    else "json"
                ),
                temperature=temperature,
            )

            content = response["message"][
                "content"
            ]

            return content

        except Exception as error:

            last_error = error

            print(
                "[qwen] JSON request failed "
                f"(attempt {attempt}/"
                f"{MAX_RETRIES}): "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

    # -----------------------------------------------------
    # All retries failed.
    # -----------------------------------------------------

    raise RuntimeError(
        "Qwen JSON request failed after "
        f"{MAX_RETRIES} attempts."
    ) from last_error