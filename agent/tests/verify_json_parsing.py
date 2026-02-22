
import asyncio
import sys
import os
import json
from unittest.mock import AsyncMock, MagicMock

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflow.med_gemma_27b.nodes.diagnosis_node import DiagnosisNode
from app.core.models import AgentState, DiagnosisResult
from langchain_core.messages import HumanMessage, AIMessage

from langchain_core.runnables import RunnableLambda

async def main():
    print("--- Verifying DiagnosisNode JSON Parsing ---")
    
    expected_json = {
        "reasoning": "Symptoms align with contact dermatitis.",
        "differential_diagnosis": ["Contact Dermatitis", "Eczema", "Insect Bite"],
        "next_step": "ask_question",
        "question": "Have you used any new soap recently?",
        "final_diagnosis": None,
        "is_critical": False,
        "confidence": 0.6
    }
    
    # Create a Runnable that returns the AIMessage
    async def mock_call(input, config=None):
        return AIMessage(content=json.dumps(expected_json))
        
    mock_llm = RunnableLambda(mock_call)
    
    node = DiagnosisNode(mock_llm)
    
    state = {
        "messages": [HumanMessage(content="My arm is itchy.")],
        "context": "Context",
        "diagnosis_progress": []
    }
    
    print("Running DiagnosisNode...")
    try:
        result = await node(state, config={})
        print("Result:", result)
        
        # Verify
        if result["next_step"] == "ask_question" and result["diagnostic_question"] == expected_json["question"]:
            print("SUCCESS: JSON Parsed correctly and next_step is 'ask_question'.")
        else:
            print("FAILURE: Result mismatch.")
            
    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
