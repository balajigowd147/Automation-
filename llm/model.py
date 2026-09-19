import ollama

from llm.schemas import AssignmentAnalysis


# --------------------------------
# LLM configuration
# --------------------------------

MODEL_NAME = "qwen3:latest"


# --------------------------------
# Analyze assignment
# --------------------------------

def analyze_with_llm(prompt):

    response = ollama.chat(
        model=MODEL_NAME,

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        format=AssignmentAnalysis.model_json_schema(),

        options={
            "temperature": 0
        }
    )

    # Get JSON text returned by Ollama
    raw_response = response["message"]["content"]

    # Validate JSON against our Pydantic model
    analysis = AssignmentAnalysis.model_validate_json(
        raw_response
    )

    return analysis