# Ref. https://langfuse.com/guides/cookbook/example_evaluating_multi_turn_conversations

import logging
import os, pytest, json, logging

from langfuse import observe, Evaluation
from tests.evals.utils.langfuse_client import LangfuseClient
from tests.evals.datasets.definite_diagnosis import local_data
from app.prompts.definite_diagnosis import get_system_message
from openevals.llm import create_llm_as_judge

os.environ["OPENAI_BASE_URL"] = "http://ollama:11434/v1"
os.environ["OPENAI_API_KEY"] = "ollama"

interview_model="gemma3n:e4b"
diagnosis_model="medgemma-1.5:4b"
judge_model="openai:qwen3:4b"
conversation_history = []
JUDGE_PROMPT = """
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
  Assign a score of relevant between "output" and "reference output" based on the following criteria:
  - 0: The output is entirely incorrect, irrelevant, or hallucinates symptoms not present in the input.
  - 0.25: The output identifies the core medical concern/symptom but fails to justify the definite diagnosis.
  - 0.5: The output identifies the concern and provides a partial or slightly flawed justification for the definite diagnosis.
  - 0.75: The output is mostly correct, identifying the concern and providing logical justification for the definite diagnosis, with only minor omissions or minor lack of clarity.
  - 1: The output is comprehensive, perfectly accurate, and aligns with the reference logic for the definite diagnosis.
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
judge = create_llm_as_judge(
    model=judge_model,
    choices=[0.0, 0.25, 0.5, 0.75, 1.0],
    prompt=JUDGE_PROMPT,
)

@pytest.fixture
def langfuse_client():
    """Initialize Langfuse client for testing"""
    return lfc.langfuse if lfc.langfuse is not None else None

# ------------------------------------------------------------------

def is_langfuse_available():
    return lfc.langfuse is not None

def setup_prompt(lfc, item):
    # item reference to dataset item
    logging.debug(f"item: {item}")
    
    if isinstance(item.input, dict):
        state = item.input
        input_content = json.dumps(item.input, ensure_ascii=False, indent=2)
    else:
        try:
            # Strip markdown markers if present
            input_str = item.input.replace("```json", "").replace("```", "").strip()
            state = json.loads(input_str)
            input_content = item.input
        except Exception as e:
            logging.error(f"Failed to parse item.input as JSON: {e}. Raw input: {item.input}")
            state = {} # Fallback
            input_content = item.input

    # load prompt from langfuse if exists, 
    # otherwise upsert prompt to langfuse to record it to be an evident
    prompt = lfc.load_prompt(
        "med-mirror/definite-diagnosis/system-message", 
        prompt_type='chat', 
        prompt=[get_system_message()],
        labels=['production']
    )
    # assign to template
    prompt = prompt.compile(
        context=state.get("context", "No context"), 
        language=state.get("language", "English")
    )

    prompt.append({"role": "user", "content": input_content})
    
    logging.debug(f"\n\nPrompt: {prompt}")
    return prompt

def task(*, item, **kwargs):

    logging.debug(f"task item: {item}")

    if not is_langfuse_available():
        return "Langfuse is not available"

    response = lfc.client.chat.completions.create(
        model=diagnosis_model,
        messages=setup_prompt(lfc, item),
        temperature=0,
        max_tokens=2048
    )

    logging.debug(f"\n\nResponse: {response.choices[0].message.content}")
    return response.choices[0].message.content

def accuracy_evaluator(*, input, output, expected_output, **kwargs):
    logging.debug(f"\n\ninput: {input}")
    logging.debug(f"\n\noutput: {output}")
    logging.debug(f"\n\nexpected_output: {expected_output}")

    v = 0.0
    try:
        prompt = JUDGE_PROMPT.format(
            inputs=input, 
            outputs=output, 
            reference_outputs=expected_output
        )
        logging.debug(f"\n\nJUDGE_PROMPT: {prompt}")
        
        # LLM Judge for Analysis (Requires inputs, outputs, AND reference_outputs)
        
        if isinstance(output, str) and isinstance(expected_output, str):
            try:
                result = judge(
                    inputs=input, 
                    outputs=output,
                    reference_outputs=expected_output
                )
                logging.debug(f"\n\nJudge result: {result}")
                # Safely extract score (usually 0.0 to 1.0)
                v += float(result.get('score', 0))
            except Exception as e:
                logging.error(f"Judge failed: {e}")

    except Exception as e:
        logging.error(f"Accuracy evaluator failed: {e}")

    return Evaluation(name="accuracy", value=v)

def average_accuracy_evaluator(*, item_results, **kwargs):
    """Run evaluator that calculates average accuracy across all items"""
    logging.debug(f"item_results: {item_results}")

    try:
        accuracies = [
            eval.value for result in item_results
            for eval in result.evaluations if eval.name == "accuracy"
        ]
    
        if not accuracies:
            return Evaluation(name="avg_accuracy", value=0)
    
        avg = sum(accuracies) / len(accuracies)
    except Exception as e:
        logging.error(f"Average accuracy evaluator failed: {e}")
        return Evaluation(name="avg_accuracy", value=0)
 
    return Evaluation(name="avg_accuracy", value=avg, comment=f"Average accuracy: {avg:.2%}")

# ------------------------------------------------------------------

def test_accuracy_passes(langfuse_client):
    """Test that passes when accuracy is above threshold"""
    #logging.debug(f"\n\nlocal_data: {local_data}")
    dataset = lfc.load_dataset(name="med-mirror/definite-diagnosis", local_data=local_data)
    logging.debug(f"Dataset items: {len(dataset.items)}")
    result = dataset.run_experiment(
        name="Definite Diagnosis Test - Should Pass",
        description="Testing all definite diagnosis cases",
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
