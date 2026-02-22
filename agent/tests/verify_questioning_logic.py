
import asyncio
import sys
import os
import json
from langchain_core.messages import HumanMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agent_graph import agent_service

async def main():
    print("--- Verifying Diagnosis Question Generation ---")
    
    # Test Case: User gives partial info.
    # Expectation: Agent asks for missing info (e.g., Duration, History)
    
    inputs = {
        "messages": [HumanMessage(content="I have a red rash on my arm.")],
        "context": "User is 30yo male.",
        # We start fresh, no pre-filled extraction
    }
    
    # We use the real graph with the real LLM (configured in env)
    # Ensure LLM_BASE_URL is pointing to something valid (local or remote)
    # The previous verify script set it to localhost:11434/v1
    os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
    
    graph = agent_service.get_graph()
    
    import uuid
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print("Streaming...")
    async for chunk in graph.astream(inputs, config=config, stream_mode="updates"):
        for node, values in chunk.items():
            print(f"Node: {node}")
            if node == "diagnosis":
                next_step = values.get("next_step")
                question = values.get("diagnostic_question")
                print(f"  Next Step: {next_step}")
                print(f"  Question: {question}")
                
                if next_step == "ask_question" and question:
                    print("SUCCESS: Agent asked a question.")
                    return
                elif next_step == "explain":
                    print("FAILURE: Agent jumped to explanation without gathering details.")
                    print(f"  Diagnosis: {values.get('diagnosis')}")
                    return

if __name__ == "__main__":
    asyncio.run(main())
