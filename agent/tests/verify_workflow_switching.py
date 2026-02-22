
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to reload agent_service because it instantiates on import
import importlib
from app.services import agent_graph

async def verify_switching():
    print("--- Verifying Workflow Switching ---")
    
    # Test 1: Default (med_gemma_4b)
    print("\n1. Testing Default (med_gemma_4b)...")
    if "ACTIVE_WORKFLOW" in os.environ:
        del os.environ["ACTIVE_WORKFLOW"]
    
    importlib.reload(agent_graph)
    service = agent_graph.agent_service
    print(f"Loaded workflow: {service.active_workflow}")
    if service.active_workflow != "med_gemma_4b":
        print("FAIL: Default should be med_gemma_4b")
    else:
        print("SUCCESS: Default is med_gemma_4b")

    # Test 2: Explicit med_gemma_27b
    print("\n2. Testing med_gemma_27b...")
    os.environ["ACTIVE_WORKFLOW"] = "med_gemma_27b"
    
    importlib.reload(agent_graph)
    service = agent_graph.agent_service
    print(f"Loaded workflow: {service.active_workflow}")
    if service.active_workflow != "med_gemma_27b":
        print("FAIL: Should be med_gemma_27b")
    else:
        print("SUCCESS: Loaded med_gemma_27b")

    # Test 3: Explicit med_gemma_4b
    print("\n3. Testing med_gemma_4b explicit...")
    os.environ["ACTIVE_WORKFLOW"] = "med_gemma_4b"
    
    importlib.reload(agent_graph)
    service = agent_graph.agent_service
    print(f"Loaded workflow: {service.active_workflow}")
    if service.active_workflow != "med_gemma_4b":
        print("FAIL: Should be med_gemma_4b")
    else:
        print("SUCCESS: Loaded med_gemma_4b")

if __name__ == "__main__":
    asyncio.run(verify_switching())
