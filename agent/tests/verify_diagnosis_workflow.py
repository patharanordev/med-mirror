
import asyncio
import sys
import os
import uuid

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable for local testing BEFORE importing config
os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"

from app.services.agent_graph import agent_service
from langchain_core.messages import HumanMessage
from langgraph.types import Command

async def main():
    print("Starting verification of Diagnosis Workflow...")
    
    # 1. Start a new thread
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"--- Step 1: User Input (Symptom) ---")
    inputs = {
        "messages": [HumanMessage(content="I have a red rash on my arm, it itches.")],
        "context": "Context from UI",
        # Pre-fill extraction to skip Interview Node and go straight to Diagnosis
        "symptoms": "red rash, itch",
        "body_part": "arm",
        "duration": "2 days",
        "allergies": "none"
    }
    
    graph = agent_service.get_graph()
    
    # Run until interrupt or end
    async for event in graph.astream(inputs, config=config):
        for key, value in event.items():
            print(f"Node: {key}")
            if key == "diagnosis":
                 if "diagnostic_question" in value:
                     print(f"  Question: {value['diagnostic_question']}")
    
    # Check state
    snapshot = await graph.aget_state(config)
    print(f"\nState after Step 1. Next: {snapshot.next}")
    
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        print("Graph is INTERRUPTED (Waiting for input). SUCCESS.")
        
        # 2. Provide Answer
        print(f"\n--- Step 2: Provide Answer ---")
        resume_command = Command(resume={"interrupt_response": "It started 2 days ago. No allergies."})
        
        async for event in graph.astream(resume_command, config=config):
            for key, value in event.items():
                print(f"Node: {key}")
                if key == "explain":
                    print(f"  Diagnosis: {value.get('diagnosis')}")
                    print(f"  Explanation: {value.get('messages')[0].content}")
                    
        print("\nVerification Workflow END.")
    else:
        print("Graph did NOT interrupt. It might have gone straight to diagnosis or failed.")

if __name__ == "__main__":
    asyncio.run(main())
