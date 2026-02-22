
from langgraph.graph import StateGraph, END
from app.core.models import AgentState
from app.workflow.diagnosis_4b.nodes import EvaluationNode, AskerNode, DefiniteDiagnosisNode

def build_diagnosis_subgraph(llm_asker, llm_diagnosis):
    # Initialize Nodes with specific LLMs
    evaluation_node = EvaluationNode(llm_asker)
    asker_node = AskerNode(llm_asker) 
    definite_diagnosis_node = DefiniteDiagnosisNode(llm_diagnosis)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("evaluation", evaluation_node)
    workflow.add_node("asker", asker_node)
    workflow.add_node("definite_diagnosis", definite_diagnosis_node)
    
    workflow.set_entry_point("evaluation")
    
    def route_evaluation(state):
        # Check if we have missing keys
        missing = state.get("missing_keys")
        if missing and len(missing) > 0:
            return "asker"
        return "definite_diagnosis"

    workflow.add_conditional_edges("evaluation", route_evaluation, {
        "asker": "asker",
        "definite_diagnosis": "definite_diagnosis"
    })
    
    # After asker gets the answer (via interrupt), we loop back to evaluation to extract info
    workflow.add_edge("asker", "evaluation")
    
    # Diagnosis is final step of this subgraph
    workflow.add_edge("definite_diagnosis", END)
    
    return workflow.compile()
