import sys
import os

# Add the 'agent' directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

try:
    from app.services.agent_graph import agent_service
    print("SUCCESS: agent_service imported.")
    
    graph = agent_service.get_graph()
    print("SUCCESS: Graph built successfully.")
    
    # Print node names to verify
    print("Nodes:", graph.nodes.keys())
    
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
