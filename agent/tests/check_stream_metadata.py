
import asyncio
import sys
import os
from langchain_core.messages import HumanMessage

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agent_graph import agent_service

async def main():
    print("--- Checking Stream Metadata ---")
    
    inputs = {
        "messages": [HumanMessage(content="hi")],
        "context": "Context"
    }
    
    graph = agent_service.get_graph()
    
    print("Streaming with mode=['messages']...")
    config = {"configurable": {"thread_id": "test_meta"}}
    async for chunk in graph.astream(inputs, config=config, stream_mode=["messages"]):
        mode, data = chunk
        if mode == "messages":
            msg, metadata = data
            # Print metadata keys to confirm 'langgraph_node' exists
            # We break after first few chunks
            print(f"Metadata keys: {list(metadata.keys())}")
            if "langgraph_node" in metadata:
                print(f"Node: {metadata['langgraph_node']}")
                break
            else:
                print("WARNING: 'langgraph_node' not found in metadata!")
                break

if __name__ == "__main__":
    asyncio.run(main())
