# Ref. https://langfuse.com/guides/cookbook/example_evaluating_multi_turn_conversations

import logging
import os, pytest, json, logging

from langfuse import observe, Evaluation
from tests.evals.utils.langfuse_client import LangfuseClient
from tests.evals.datasets.thinking import local_data
from app.prompts.thinking import system_message
from app.models.graph_states.thinking_result_simple import ThinkingResultSimple
from langchain_core.output_parsers import JsonOutputParser
from openevals.llm import create_llm_as_judge

# THINKING_ANALYSIS_JUDGE_PROMPT = """
# You are an expert medical intent analyzer evaluator. Your task is to assess the quality of an LLM's reasoning (analysis) compared to a reference analysis.

# Input: {{inputs}}
# LLM Output Analysis: {{outputs}}
# Reference Analysis: {{reference_outputs}}

# Assign a score of 0, 0.25, 0.5, 0.75, or 1 based on the following criteria:

# - 0: The analysis is entirely incorrect, irrelevant, or hallucinates symptoms not present in the input.
# - 0.25: The analysis identifies the core medical concern/symptom but fails to justify the routing or shopping intent.
# - 0.5: The analysis identifies the concern and provides a partial or slightly flawed justification for the routing or shopping intent.
# - 0.75: The analysis is mostly correct, identifying the concern and providing logical justification for both routing and shopping intent, with only minor omissions or minor lack of clarity.
# - 1: The analysis is comprehensive, perfectly accurate, and aligns with the reference logic for routing and shopping intent.

# Provide your feedback in the following format:
# {{
#   "score": <score>,
#   "reasoning": "<brief explanation of the score>"
# }}
# """

os.environ["OPENAI_BASE_URL"] = "http://ollama:11434/v1"
os.environ["OPENAI_API_KEY"] = "ollama"

interview_model="gemma3n:e4b"
diagnosis_model="medgemma-1.5:4b"
judge_model="openai:qwen3:4b"
conversation_history = []
THINKING_ANALYSIS_JUDGE_PROMPT = """
You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:

<Rubric>
  A correct answer:
  - Provides accurate and complete information
  - Contains no factual errors
  - Addresses all parts of the question
  - Is logically consistent
  - Uses precise and accurate terminology
  When scoring, you should penalize:
  - Factual errors or inaccuracies
  - Incomplete or partial answers
  - Misleading or ambiguous statements
  - Incorrect terminology
  - Logical inconsistencies
  - Missing key information
  Assign a score of 0, 0.25, 0.5, 0.75, or 1 based on the following criteria:
  - 0: The analysis is entirely incorrect, irrelevant, or hallucinates symptoms not present in the input.
  - 0.25: The analysis identifies the core medical concern/symptom but fails to justify the routing or shopping intent.
  - 0.5: The analysis identifies the concern and provides a partial or slightly flawed justification for the routing or shopping intent.
  - 0.75: The analysis is mostly correct, identifying the concern and providing logical justification for both routing and shopping intent, with only minor omissions or minor lack of clarity.
  - 1: The analysis is comprehensive, perfectly accurate, and aligns with the reference logic for routing and shopping intent.
</Rubric>
<Instructions>
  - Carefully read the input and output
  - Check for factual accuracy and completeness
  - Focus on correctness of information rather than style or verbosity
</Instructions>
<Reminder>
  The goal is to evaluate factual correctness and completeness of the response.
</Reminder>
<input>
{inputs}
</input>
<output>
{outputs}
</output>
Use the reference outputs below to help you evaluate the correctness of the response:
<reference_outputs>
{reference_outputs}
</reference_outputs>
"""

lfc = LangfuseClient()
parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)
judge = create_llm_as_judge(
    model=judge_model,
    choices=[0.0, 0.25, 0.5, 0.75, 1.0],
    prompt=THINKING_ANALYSIS_JUDGE_PROMPT,
)

# ------------------------------------------------------------------

@pytest.fixture
def langfuse_client():
    """Initialize Langfuse client for testing"""
    return lfc.langfuse if lfc.langfuse is not None else None

def is_langfuse_available():
    return lfc.langfuse is not None

def task(*, item, **kwargs):
    question = item["input"]

    if not is_langfuse_available():
        return "Langfuse is not available"

    response = lfc.client.chat.completions.create(
        model=interview_model,
        messages=[
            { 
                "role": "system", 
                "content": system_message.format(
                    context="No context", 
                    format_instructions=parser.get_format_instructions()
                )
            },
            { "role": "user", "content": question }
        ],
        temperature=0,
        max_tokens=2048
    )

    return response.choices[0].message.content

def accuracy_evaluator(*, input, output, expected_output, **kwargs):
    # Ensure inputs are dicts (parsing logic from previous steps)
    if isinstance(output, str):
        output = json.loads(output.replace("```json", "").replace("```", "").strip())
    if isinstance(expected_output, str):
        expected_output = json.loads(expected_output.replace("```json", "").replace("```", "").strip())

    v = 0.0

    prompt = THINKING_ANALYSIS_JUDGE_PROMPT.format(
        inputs=input, 
        outputs=output, 
        reference_outputs=expected_output
    )
    logging.info(f"\n\nTHINKING_ANALYSIS_JUDGE_PROMPT: {prompt}")
    
    # LLM Judge for Analysis (Requires inputs, outputs, AND reference_outputs)
    if output.get('analysis'):
        try:
            analysis_result = judge(
                inputs=input, 
                outputs=output.get('analysis'),
                reference_outputs=expected_output.get('analysis') # Fixes 'reference_outputs' error
            )
            logging.info(f"\n\nAnalysis result: {analysis_result}")
            # Safely extract score (usually 0.0 to 1.0)
            v += float(analysis_result.get('score', 0))
        except Exception as e:
            logging.error(f"Judge failed: {e}")

    # Exact Match for categorical fields
    fields = ['next_step', 'language', 'shopping_intent']
    for field in fields:
        if expected_output.get(field) == output.get(field):
            v += 1.0

    return Evaluation(name="accuracy", value=v/(len(fields)+1))

def average_accuracy_evaluator(*, item_results, **kwargs):
    """Run evaluator that calculates average accuracy across all items"""
    accuracies = [
        eval.value for result in item_results
        for eval in result.evaluations if eval.name == "accuracy"
    ]
 
    if not accuracies:
        return Evaluation(name="avg_accuracy", value=0)
 
    avg = sum(accuracies) / len(accuracies)
 
    return Evaluation(name="avg_accuracy", value=avg, comment=f"Average accuracy: {avg:.2%}")

# ------------------------------------------------------------------

def test_accuracy_passes(langfuse_client):
    """Test that passes when accuracy is above threshold"""
    result = langfuse_client.run_experiment(
        name="Dark Circle Test - Should Pass",
        description="Testing dark circle case conversation",
        data=local_data,
        task=task,
        evaluators=[accuracy_evaluator],
        run_evaluators=[average_accuracy_evaluator]
    )

    # Use format method to display results
    logging.info(result.format())
 
    # Access the run evaluator result directly
    avg_accuracy = next(
        eval.value for eval in result.run_evaluations
        if eval.name == "avg_accuracy"
    )
    
    logging.info(avg_accuracy)
 
    # Assert minimum accuracy threshold
    assert avg_accuracy >= 0.7, f"Average accuracy {avg_accuracy:.2f} below threshold 0.7"

    langfuse_client.flush()
