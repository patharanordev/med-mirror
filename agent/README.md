# Medical Agent

This directory contains the Python-based medical AI agent that runs via FastAPI and LangGraph.

## Workflows & Model Configuration

The agent supports two distinct workflows tailored for different model sizes and computational resources. You can switch between them by setting the `ACTIVE_WORKFLOW` environment variable in your `.env` file.

### 1. `med_gemma_4b` (Default / Edge)
Optimized for speed and lower resource usage (e.g., local laptops, edge devices).
- **Workflow Logic**: `app/workflow/med_gemma_4b/graph.py`
- **Recommended Models**:
  - Main LLM: `qwen3:1.7b` (or similar lightweight model)
  - Diagnosis LLM: `medgemma-1.5:4b`

**Configuration (.env):**
```bash
ACTIVE_WORKFLOW=med_gemma_4b
LLM_MODEL=qwen3:1.7b
LLM_MODEL_DIAGNOSIS=medgemma-1.5:4b
```

| Workflow for MedGemma1.5:4b | Diagnosis Subgraph |
|-----------------------------|--------------------|
|![ex-graph-for-medgemma4b](./assets/images/ex-graph-medgemma-4b.png) | ![ex-diagnosis-subgraph](./assets/images/ex-diagnosis_subgraph.png)|

### 2. `med_gemma_27b` (High Accuracy)
Optimized for deep medical reasoning and higher accuracy. Requires significantly more VRAM.
- **Workflow Logic**: `app/workflow/med_gemma_27b/graph.py`
- **Recommended Models**:
  - Main LLM: `qwen3:8b` (or larger)
  - Diagnosis LLM: `medgemma:27b`

**Configuration (.env):**
```bash
ACTIVE_WORKFLOW=med_gemma_27b
LLM_MODEL=qwen3:8b
LLM_MODEL_DIAGNOSIS=medgemma:27b
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
    -   If **False**, the session ends normally.

This replaces the previous "Human-in-the-Loop" question node, providing a smoother and faster user experience.
