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


QWEN_MODEL = "qwen3:latest"

OLLAMA_HOST = "http://localhost:11434"

QWEN_NUM_CTX = 8192

QWEN_TIMEOUT = 180

MAX_RETRIES = 3

RETRY_DELAY = 2

KEEP_ALIVE = "10m"



client = Client(
    host=OLLAMA_HOST,
    timeout=QWEN_TIMEOUT,
)


def _call_qwen(
    messages,
    *,
    response_format=None,
    temperature=0.2,
):

    return client.chat(
        model=QWEN_MODEL,
        messages=messages,

        think=False,


        format=response_format,

        options={
            "temperature": temperature,
            "num_ctx": QWEN_NUM_CTX,
        },


        keep_alive=KEEP_ALIVE,
    )


def ask_qwen(
    prompt,
    *,
    system=None,
    temperature=0.2,
):


    messages = []


    if system:

        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )


    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    last_error = None


    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = _call_qwen(
                messages,
                temperature=temperature,
            )

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


    raise RuntimeError(
        "Qwen request failed after "
        f"{MAX_RETRIES} attempts."
    ) from last_error

def ask_qwen_json(
    prompt,
    *,
    schema=None,
    system=None,
    temperature=0.0,
):
   
    messages = []


    if system:

        messages.append(
            {
                "role": "system",
                "content": system,
            }
        )


    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    last_error = None


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

    raise RuntimeError(
        "Qwen JSON request failed after "
        f"{MAX_RETRIES} attempts."
    ) from last_error