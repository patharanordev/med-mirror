from langgraph.graph import StateGraph, END
from app.core.models import AgentState
from app.workflow.med_gemma_4b.nodes.diagnosis.nodes import AskerNode
from app.workflow.med_gemma_4b.nodes.diagnosis_node import DiagnosisNode

def build_diagnosis_subgraph(llm, llm_diagnosis):
    asker = AskerNode(llm)
    diagnosis = DiagnosisNode(llm_diagnosis)
    
    workflow = StateGraph(AgentState)
    workflow.add_node("asker", asker)
    workflow.add_node("diagnosis", diagnosis)
    
    workflow.set_entry_point("asker")
    
    def route_asker(state):
        if state.get("diagnosis_complete"):
            return "diagnosis"
        return END

    workflow.add_conditional_edges("asker", route_asker, {
        "diagnosis": "diagnosis",
        END: END
    })
    
    workflow.add_edge("diagnosis", END)
    
    return workflow.compile()
