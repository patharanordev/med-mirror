import os
import sys
import asyncio
from langchain_core.messages import HumanMessage, AIMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflow.med_gemma_4b.nodes.diagnosis.graph import build_diagnosis_subgraph
from app.services.agent_graph import agent_service
from app.core.models import AgentState

async def test_isolated_subgraph():
    print("--- Verifying Diagnosis Subgraph (Isolated) ---")
    
    # Use real LLMs from agent_service
    llm = agent_service.llm
    llm_diagnosis = agent_service.llm_diagnosis
    
    # Build ONLY the subgraph
    graph = build_diagnosis_subgraph(llm, llm_diagnosis)
    
    # 1. Start with a symptom
    # We simulate that the parent graph routed here, so we have a user message.
    print("\n[Step 1] User: I have a rash on my arm.")
    input_state = {
        "messages": [HumanMessage(content="I have a rash on my arm.")],
        "patient_info": {},    # Initialize if needed
        "missing_keys": None   # Force recalc
    }
    
    config = {"configurable": {"thread_id": "test_iso_001"}}
    
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
                
    # 2. Reply to question
    # We expect AskNode to return a message.
    # We simulate the NEXT turn.
    # Note: Subgraph execution ENDs after asking.
    # Next turn, we re-enter the subgraph.
    # But we need to preserve state. `astream` on a compiled graph with checkpointer would preserve state.
    # But `build_diagnosis_subgraph` returns a compiled graph WITHOUT checkpointer in implementation?
    # Let's check `graph.py`. `return workflow.compile()`. No checkpointer passed in `build_diagnosis_subgraph`.
    # So we need to pass checkpointer OR explicitly pass state.
    # If we pass state, we need to merge output state from step 1.
    
    # Actually, we can just feed the output state back in.
    # But `astream` yields updates.
    # We can use `ainvoke` to get final state of the run?
    # `ainvoke` returns the final state.
    
    print("\n[Step 1 - Invoke]")
    result_state_1 = await graph.ainvoke(input_state)
    print(f"State after Step 1: PatientInfo={result_state_1.get('patient_info')}")
    print(f"Last Message: {result_state_1['messages'][-1].content}")
    
    # Step 2: User answers
    print("\n[Step 2] User: It started 2 days ago.")
    # Append user message to history
    new_messages = result_state_1['messages'] + [HumanMessage(content="It started 2 days ago.")]
    input_state_2 = {
        **result_state_1,
        "messages": new_messages
    }
    
    result_state_2 = await graph.ainvoke(input_state_2)
    print(f"State after Step 2: PatientInfo={result_state_2.get('patient_info')}")
    print(f"Last Message: {result_state_2['messages'][-1].content}")
    
    # Step 3: Provide all info (cheat)
    print("\n[Step 3] User Provides All Info")
    # Manually fill patient info to test completion
    input_state_3 = {
        **result_state_2,
        "patient_info": {
            "onset_and_duration": "2 days",
            "location_and_spread": "Arm",
            "associated_symptoms": "Itching",
            "medical_background": "None",
            "triggers": "None",
            "diet_history": "Normal",
            "lifestyle_and_sleep": "Good"
        },
        "messages": result_state_2['messages'] + [HumanMessage(content="Here is everything else: itching, no history, no triggers, normal diet, good sleep.")]
    }
    
    result_state_3 = await graph.ainvoke(input_state_3)
    print(f"State after Step 3: Diagnosis Complete={result_state_3.get('diagnosis_complete')}")
    print(f"Next Step: {result_state_3.get('next_step')}")
    if result_state_3.get('diagnosis'):
        print(f"Diagnosis: {result_state_3['diagnosis']}")

if __name__ == "__main__":
    asyncio.run(test_isolated_subgraph())
