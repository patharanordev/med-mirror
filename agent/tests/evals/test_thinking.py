# Ref. https://langfuse.com/guides/cookbook/example_evaluating_multi_turn_conversations

import pytest, json, logging

from langfuse import observe, Evaluation
from tests.evals.utils.langfuse_client import LangfuseClient
from tests.evals.datasets.dark_circle import local_data
from app.prompts.thinking import system_message
from app.models.graph_states.thinking_result_simple import ThinkingResultSimple
from langchain_core.output_parsers import JsonOutputParser

interview_model="gemma3n:e4b"
diagnosis_model="medgemma-1.5:4b"
conversation_history = []

lfc = LangfuseClient()
parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)

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
    logging.info(f'\n\noutput: {output}')
    logging.info(f'\n\nexpected_output: {expected_output}')
    
    if isinstance(output, str):
        try:
            output = output.replace("```json", "").replace("```", "").strip()
            logging.info(f'\n\noutput: {output}')
            output = json.loads(output)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse output: {output}")
            return Evaluation(name="accuracy", value=0.0)

    if isinstance(expected_output, str):
        try:
            expected_output = expected_output.replace("```json", "").replace("```", "").strip()
            logging.info(f'\n\nexpected_output: {expected_output}')
            expected_output = json.loads(expected_output)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse expected_output: {expected_output}")
            return Evaluation(name="accuracy", value=0.0)

    v = 0
    if expected_output.get('reasoning') == output.get('reasoning'):
        v += 1
    if expected_output.get('next_step') == output.get('next_step'):
        v += 1
    if expected_output.get('language') == output.get('language'):
        v += 1
    if expected_output.get('shopping_intent') == output.get('shopping_intent'):
        v += 1

    return Evaluation(name="accuracy", value=v/4)

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
