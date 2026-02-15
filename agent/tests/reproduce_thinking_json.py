
import asyncio
import sys
import os
import json
from unittest.mock import AsyncMock
from langchain_core.messages import AIMessage, HumanMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflow.med_gemma_27b.nodes.thinking_node import ThinkingNode
from app.core.models import AgentState

# Mock LLM that returns the problematic string seen by user
problematic_output = """{
  "analysis": "Dark circles under eyes may indicate sleep deprivation, allergies, or dehydration.",
  "next_step": "diagnosis",
  "todo": [
    "Ask about duration of dark circles",
    "Check for itching, swelling, or redness around eyes",
    "Inquire about sleep quality and stress levels"
  ]
}ขอบตาหมีแพนด้า! วิเคราะห์เบื้องต้นว่าเป็นรอยคล้ำจากความเครียดหรือไม่? 🕵️"""

async def main():
    print("--- Reproducing ThinkingNode JSON Issue ---")
    
    mock_llm = AsyncMock()
    # Mock behavior: with_structured_output returns a chain that eventually returns the raw text 
    # if the model doesn't support tools, OR if we use a parser that fails.
    # However, ThinkingNode currently uses: chain = prompt | llm.with_structured_output(...)
    
    # If we want to simulate the failure, we need to know what llm.with_structured_output returns when it fails.
    # Typically, if it can't parse, it raises an error.
    # But the user sees the RAW content in the debug log.
    # This implies the node DID return something, likely a dict (if successful) or the raw string?
    
    # If the user sees: "content": "{\"thinking\": \"\", ... \"text\": \"{...}\" ...}"
    # The "text" field seems to contain the JSON string + Thai text.
    # This structure `{"thinking": "", "plan": "", "text": "..."}` usually comes from the backend streaming logic 
    # wrapping the node output?
    
    # Let's verify what ThinkingNode returns.
    # It returns {"todo": ..., "next_step": ...} dictionary.
    
    # Create a Runnable that returns the problematic output as AIMessage
    from langchain_core.runnables import RunnableLambda
    async def mock_call(input, config=None):
        return AIMessage(content=problematic_output)
        
    mock_llm = RunnableLambda(mock_call)
    
    node = ThinkingNode(mock_llm)
    
    state = {
        "messages": [HumanMessage(content="My eyes are dark.")],
        "context": "Context"
    }
    
    print("Running ThinkingNode with problematic output...")
    try:
        result = await node(state, config={})
        print("Result:", result)
        
        if result["next_step"] == "diagnosis" and len(result["todo"]) > 0:
            print("SUCCESS: ThinkingNode handled the messy JSON correctly.")
        else:
            print("FAILURE: Result mismatch.")
            
    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
