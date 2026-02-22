
import sys
import os

# Add agent directory to path
sys.path.append(os.path.abspath("agent"))

from app.workflow.med_gemma_4b.graph import build_graph
from langgraph.checkpoint.memory import MemorySaver

class MockLLM:
    def __init__(self, name):
        self.name = name
    def invoke(self, *args, **kwargs):
        return "Mock response"
    async def ainvoke(self, *args, **kwargs):
        class MockMessage:
            content = "Mock response"
        return MockMessage()
        
    def with_config(self, *args, **kwargs):
        return self

def verify_graph():
    llm = MockLLM("gemma3n")
    llm_diagnosis = MockLLM("medgemma4b")
    checkpointer = MemorySaver()
    
    try:
        graph = build_graph(llm, llm_diagnosis, checkpointer)
        print("Graph built successfully!")
        
        # Visualize to PNG to check structure if possible, but just building is good
        try:
            png_bytes = graph.get_graph().draw_mermaid_png()
            with open("agent/output/diagnosis_4b_test.png", "wb") as f:
                f.write(png_bytes)
            print("Graph visualization saved to agent/output/diagnosis_4b_test.png")
        except Exception as e:
            print(f"Visualization failed (maybe missing dependencies like graphviz?): {e}")

    except Exception as e:
        print(f"Graph verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_graph()
