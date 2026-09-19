import ollama

from llm.schemas import AssignmentAnalysis


MODEL_NAME = "qwen3:latest"

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


    raw_response = response["message"]["content"]

    analysis = AssignmentAnalysis.model_validate_json(
        raw_response
    )

    return analysis