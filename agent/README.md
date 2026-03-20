# Medical Agent

This directory contains the Python-based medical AI agent that runs via FastAPI and LangGraph.

## Workflows & Node Explanation

The agent supports two distinct workflows tailored for different model sizes and computational resources. You can switch between them by setting the `ACTIVE_WORKFLOW` environment variable in your `.env` file.

## `med_gemma_4b` Workflows & Node Explanation

The `med_gemma_4b` architecture is structured through LangGraph to manage intent routing, casual conversation, medical data extraction, diagnosis, and product recommendation using three specific LLMs: the Main LLM (`gemma3n:e4b`), the Diagnosis LLM (`medgemma-1.5:4b`), and the Tool Call LLM (`qwen3:4b`).

### Main Workflow Nodes (`app/workflow/med_gemma_4b/graph.py`)
- **`thinking` (ThinkingNode)**: Evaluates user input and routes to general chat, diagnosis, or shopping search. Uses the **Main LLM**.
- **`general_chat` (GeneralChatNode)**: Handles casual conversation securely and concisely. Uses the **Main LLM**.
- **`diagnosis_process` (Diagnosis Subgraph)**: Specialized subgraph (below) dedicated to conducting medical interviews and diagnosing. 
- **`explain` (ExplainNode)**: Takes the final clinical diagnosis output from `diagnosis_process` and transforms it into a patient-friendly explanation. Uses the **Main LLM**.
- **`ask_treatment` (AskTreatmentNode)**: Proactively checks if the user wants recommendations for treatments, medicine, or relevant medical centers. If YES, it sets `shopping_intent` to True. Uses the **Main LLM**.
- **`shopping_search` (ShoppingSearchNode)**: Uses the `tavily-python` internet search tool to recommend actual products based on intended conditions. Uses the specialized **Tool Call LLM**.

### Diagnosis Subgraph Nodes (`diagnosis_process`)
When entering the medical diagnosis phase, the agent routes to a dedicated Subgraph:
- **`evaluation` (EvaluationNode)**: Continuously evaluates if the medical interview state is complete. Routes to `asker` if more information is needed, or `definite_diagnosis` if complete. Uses the **Main LLM**.
- **`asker` (AskerNode)**: A Human-in-the-Loop (HITL) node that forms natural questions to collect missing medical context (symptoms, duration, etc.) and interrupts to wait for user response. Uses the **Main LLM**.
- **`definite_diagnosis` (DefiniteDiagnosisNode)**: The clinical reasoning engine calculating the final diagnosis once all required information has been collected. Uses the specialized **Diagnosis LLM**.

---

## Model Configuration

### 1. `med_gemma_4b` (Default / Edge)
Optimized for speed and lower resource usage (e.g., local laptops, edge devices).
- **Workflow Logic**: `app/workflow/med_gemma_4b/graph.py`
- **Recommended Models**:
  - Main LLM: `gemma3n:e4b` (or similar lightweight model)
  - Diagnosis LLM: `medgemma-1.5:4b`
  - Tool Call LLM: `qwen3:4b`

**Configuration (.env):**
```bash
# ------------------------------------------------------------------------------
# App Configs

# Choose workflow that match with your device
ACTIVE_WORKFLOW=med_gemma_4b

# STT Settings (Whisper model: tiny, tiny.en, base, base.en, small, small.en, medium, large-v2, large-v3)
# Use ".en" suffix for English-only models (faster but English only)
STT_MODEL_SIZE=large-v3

# Agent Language (th = Thai, en = English)
AGENT_LANGUAGE=th

# ------------------------------------------------------------------------------
# LLM

LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=ollama

# For MedGemma on small edge computing
LLM_MODEL=gemma3n:e4b
LLM_MODEL_DIAGNOSIS=medgemma-1.5:4b
LLM_MODEL_WITH_TOOL_CALL=qwen3:4b

# # For MedGemma with high accuracy
# LLM_MODEL=qwen3:8b
# LLM_MODEL_DIAGNOSIS=medgemma:27b

# ------------------------------------------------------------------------------
# Tracing (Supports both, priority depends on env vars)

# Langfuse (Explicitly initialized in app/core/config.py)
LANGFUSE_SECRET_KEY="sk-lf-be...19a07"
LANGFUSE_PUBLIC_KEY="pk-lf-ef...bfc9"
LANGFUSE_BASE_URL="http://localhost:33000"

# LangSmith (Implicitly supported via LangChain env vars)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_f5...60e92
LANGSMITH_PROJECT="MedMirror"

# ------------------------------------------------------------------------------
# Tools

# Tavily
TAVILY_API_KEY=tvly-dev-1BdX...MAnS
```

| Workflow for MedGemma1.5:4b | Diagnosis Subgraph |
|-----------------------------|--------------------|
|![ex-graph-for-medgemma4b](./assets/images/ex-graph-medgemma-4b.png) | ![ex-diagnosis-subgraph](./assets/images/ex-diagnosis_subgraph.png)|

### 2. `med_gemma_27b` (High Accuracy)

> ---
> **NOTE**: This part I didn't test with `medgemma:27b` yet. It's my future plan to test it.
>
> ---

Optimized for deep medical reasoning and higher accuracy. Requires significantly more VRAM.
- **Workflow Logic**: `app/workflow/med_gemma_27b/graph.py`
- **Recommended Models**:
  - Main LLM: `gemma3` (or larger)
  - Diagnosis LLM: `medgemma:27b`
  - Tool Call LLM: `qwen3:8b`

**Configuration (.env):**
```bash
ACTIVE_WORKFLOW=med_gemma_27b

# LLM Server Configuration
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama

# Model Configuration
LLM_MODEL=gemma3
LLM_MODEL_DIAGNOSIS=medgemma:27b
LLM_MODEL_WITH_TOOL_CALL=qwen3:8b

# Add other environment variables (STT, Tavily, LangSmith) as shown in the 4B configuration.
```

| Workflow for MedGemma:27b |
|---------------------------|
| ![ex-graph-for-medgemma27b](./assets/images/ex-graph-medgemma-27b.png) |


## Requirements

- **Python 3.12+**
  - **Critical**: You must use Python 3.12 or newer. 
  - Using older versions (3.10/3.11) may cause the error: `Called get_config outside of a runnable context` when using LangGraph's human-in-the-loop features (interrupts).

## Running Locally

1. Create a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the agent:
   ```bash
   uvicorn main:app --reload --port 8001
   ```

### Mock Endpoints (Local Testing)
To test the frontend UI (like the product recommendation carousel) without hitting the LLM or Tavily API every time, you can utilize the streaming mocks provided in the `mocks/` directory. This is particularly useful for rapid iterations on the mobile app.

## Docker

The provided Dockerfiles (`Dockerfile.win`, `Dockerfile.mac`) are already configured to use Python 3.12.

## Shopping Intent Detection

The agent now features smart **Shopping Intent Detection** powered by the LLM (`gemma3n:e4b` or routing model).

![Shopping Intent Detection](./assets/images/user-shopping-intent.jpg)

### How it works:
1.  **Thinking Node**: Detects if the user explicitly asks for products, medicine, or treatment (e.g., "I need a cream for this rash").
2.  **Evaluation Node**: Continuously monitors the diagnosis interview for shopping intent.
3.  **State Update**: Sets `shopping_intent=True` in the `AgentState`.
4.  **Automatic Routing**:
    -   If `shopping_intent` is **True**, the agent automatically transitions to **Shopping Search** after the diagnosis/explanation is complete.
    -   This node uses the `tavily-python` tool to fetch live product recommendations using your `TAVILY_API_KEY`.
    -   If **False**, the session ends normally.

This replaces the previous "Human-in-the-Loop" question node, providing a smoother and faster user experience.

## Testing

### Evaluation

Please refer to `docker-compose.eval.yml` at the root of this project.

For WinOS:

```bash
start_eval.bat
```

For Linux:

```bash
docker compose -f docker-compose.eval.yml up --build
```

Output:

```sh
eval-agent  | tests/evals/test_thinking.py::test_accuracy_passes
eval-agent  | -------------------------------- live log call ---------------------------------
eval-agent  | INFO     root:test_thinking.py:143
eval-agent  |
eval-agent  | THINKING_ANALYSIS_JUDGE_PROMPT:
eval-agent  | You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:
eval-agent  |
eval-agent  | <Rubric>
eval-agent  |   A correct answer:
eval-agent  |   - Provides accurate and complete information
eval-agent  |   - Contains no factual errors
eval-agent  |   - Addresses all parts of the question
eval-agent  |   - Is logically consistent
eval-agent  |   - Uses precise and accurate terminology
eval-agent  |   When scoring, you should penalize:
eval-agent  |   - Factual errors or inaccuracies
eval-agent  |   - Incomplete or partial answers
eval-agent  |   - Misleading or ambiguous statements
eval-agent  |   - Incorrect terminology
eval-agent  |   - Logical inconsistencies
eval-agent  |   - Missing key information
eval-agent  |   Assign a score of 0, 0.25, 0.5, 0.75, or 1 based on the following criteria:
eval-agent  |   - 0: The analysis is entirely incorrect, irrelevant, or hallucinates symptoms not present in the input.
eval-agent  |   - 0.25: The analysis identifies the core medical concern/symptom but fails to justify the routing or shopping intent.
eval-agent  |   - 0.5: The analysis identifies the concern and provides a partial or slightly flawed justification for the routing or shopping intent.
eval-agent  |   - 0.75: The analysis is mostly correct, identifying the concern and providing logical justification for both routing and shopping intent, with only minor omissions or minor lack of clarity.
eval-agent  |   - 1: The analysis is comprehensive, perfectly accurate, and aligns with the reference logic for routing and shopping intent.
eval-agent  | </Rubric>
eval-agent  | <Instructions>
eval-agent  |   - Carefully read the input and output
eval-agent  |   - Check for factual accuracy and completeness
eval-agent  |   - Focus on correctness of information rather than style or verbosity
eval-agent  | </Instructions>
eval-agent  | <Reminder>
eval-agent  |   The goal is to evaluate factual correctness and completeness of the response.
eval-agent  | </Reminder>
eval-agent  | <input>
eval-agent  | ช่วงนี้ขอบตาดำมากทายาอะไรดี
eval-agent  | </input>
eval-agent  | <output>
eval-agent  | {'analysis': 'User is describing symptoms of dark circles under the eyes and asking for medication recommendations.', 'next_step': 'diagnosis', 'language': 'Thai', 'shopping_intent': True}
eval-agent  | </output>
eval-agent  | Use the reference outputs below to help you evaluate the correctness of the response:
eval-agent  | <reference_outputs>
eval-agent  | {'next_step': 'diagnosis', 'language': 'Thai', 'shopping_intent': True, 'analysis': 'The user is asking for medication for dark circles under the eyes, indicating a potential medical concern and a desire to purchase a remedy. This suggests a shopping intent related to medicine or skincare products.'}
eval-agent  | </reference_outputs>
eval-agent  |
eval-agent  | INFO     root:test_thinking.py:153
eval-agent  |
eval-agent  | Analysis result: {'key': 'score', 'score': 0.75, 'comment': "The input is a Thai sentence meaning: 'This week, the eyelids are very dark, what medicine is good?' (referring to dark circles under the eyes and a request for medicine recommendations). The output states: 'User is describing symptoms of dark circles under the eyes and asking for medication recommendations.' This is mostly correct in identifying the core medical concern (dark circles) and the request for medicine. However, it misses key elements from the reference output: (1) The phrase 'indicating a potential medical concern' (the reference infers this from the symptom description), and (2) Explicit mention of 'shopping intent' and 'desire to purchase a remedy'. The output does not explicitly state the shopping context (i.e., the user wants to buy medicine), though it implies it through 'asking for medication recommendations'. Since the output correctly identifies the symptom and request but lacks the reference's explicit framing of medical concern and shopping intent, it falls under the 0.75 category: 'mostly correct, identifying the concern and providing logical justification for both routing and shopping intent, with only minor omissions or lack of clarity.'", 'metadata': None}
eval-agent  | INFO     root:test_thinking.py:195 Individual Results: Hidden (1 items)
eval-agent  | 💡 Set include_item_results=True to view them
eval-agent  |
eval-agent  | ──────────────────────────────────────────────────
eval-agent  | 🧪 Experiment: Dark Circle Test - Should Pass
eval-agent  | 📋 Run name: Dark Circle Test - Should Pass - 2026-03-20T04:24:03.018950Z - Testing dark circle case conversation
eval-agent  | 1 items
eval-agent  | Evaluations:
eval-agent  |   • accuracy
eval-agent  |
eval-agent  | Average Scores:
eval-agent  |   • accuracy: 0.938
eval-agent  |
eval-agent  | Run Evaluations:
eval-agent  |   • avg_accuracy: 0.938
eval-agent  |     💭 Average accuracy: 93.75%
eval-agent  |
eval-agent  | INFO     root:test_thinking.py:203 0.9375
eval-agent  | PASSED
eval-agent  |
eval-agent  | ======================== 1 passed in 105.05s (0:01:45) =========================
```

### Functional/Unit Tests

> ---
> **NOTE**: Some test scripts require Ollama to be running locally. Make sure Ollama is running before running the tests.
>
> ---

Install python3.12:

```bash
python3.12 -m venv .venv

# for winos
.\.venv\Scripts\Activate.ps1

# for linux
source .venv/bin/activate
```

Install pytest with dependencies:

```bash
pip install langchain langchain_openai pydantic_settings pytest pytest-asyncio
```

Ex. run tests:

```bash
pytest tests/test_agent_struct_output.py
```
