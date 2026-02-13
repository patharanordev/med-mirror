# Medical Agent

This directory contains the Python-based medical AI agent that runs via FastAPI and LangGraph.

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
