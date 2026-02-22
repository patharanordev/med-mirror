import os
import sys
import asyncio
from langchain_core.messages import HumanMessage, AIMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agent_graph import agent_service
from app.core.models import AgentState

async def test_diagnosis_subgraph():
    print("--- Verifying Diagnosis Subgraph ---")
    
    # Ensure we are using med_gemma_4b
    os.environ["ACTIVE_WORKFLOW"] = "med_gemma_4b"
    # Re-init service just in case (though default is 4b)
    # Actually agent_service is instantiated on import, but we can access its graph.
    
    graph = agent_service.get_graph()
    
    thread_id = "test_diagnosis_subgraph_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. Start with a symptom
    print("\n[Step 1] User: I have a rash on my arm.")
    input_state = {
        "messages": [HumanMessage(content="I have a rash on my arm.")],
    }
    
    # Manually force routing to diagnosis for testing?
    # Or let ThinkingNode decide. ThinkingNode might route to 'diagnosis'.
    # Let's trust the graph.
    
    async for event in graph.astream(input_state, config=config):
        for node, data in event.items():
            print(f"Node: {node}")
            if "messages" in data:
                print(f"  Output Messages: {data['messages']}")
            if "patient_info" in data:
                print(f"  Patient Info: {data['patient_info']}")
            if "missing_keys" in data:
                print(f"  Missing Keys: {data['missing_keys']}")
            if "diagnosis_complete" in data:
                print(f"  Diagnosis Complete: {data['diagnosis_complete']}")
            if "next_step" in data:
                print(f"  Next Step: {data['next_step']}")

    # 2. Check State
    state = await graph.aget_state(config)
    print("\n--- Current State ---")
    # print(state.values)
    patient_info = state.values.get("patient_info")
    print(f"Patient Info: {patient_info}")
    
    # 3. Reply to valid question
    # We expect the bot asked a question about Duration or Symptoms etc.
    # Let's assume it asked about Duration.
    print("\n[Step 2] User: It started 2 days ago.")
    input_state = {
        "messages": [HumanMessage(content="It started 2 days ago.")],
    }
    async for event in graph.astream(input_state, config=config):
        for node, data in event.items():
            print(f"Node: {node}")
            if "patient_info" in data:
                 print(f"  Patient Info: {data['patient_info']}")

    # 4. Check State Again
    state = await graph.aget_state(config)
    print(f"Patient Info: {state.values.get('patient_info')}")
    
if __name__ == "__main__":
    asyncio.run(test_diagnosis_subgraph())
