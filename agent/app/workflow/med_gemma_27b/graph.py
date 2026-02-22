
from langgraph.graph import StateGraph, END
from app.core.models import AgentState

# Import Nodes for 27b
from app.workflow.med_gemma_27b.nodes.thinking_node import ThinkingNode
from app.workflow.med_gemma_27b.nodes.general_chat_node import GeneralChatNode
from app.workflow.med_gemma_27b.nodes.interview_node import InterviewNode
from app.workflow.med_gemma_27b.nodes.diagnosis_node import DiagnosisNode
from app.workflow.med_gemma_27b.nodes.shopping_search_node import ShoppingSearchNode
from app.workflow.med_gemma_27b.nodes.explain_node import ExplainNode

def build_graph(llm, llm_diagnosis, llm_tool_call, checkpointer, tavily_tool=None):
    # Initialize Nodes
    thinking_node = ThinkingNode(llm)
    general_chat_node = GeneralChatNode(llm)
    interview_node = InterviewNode(llm)
    diagnosis_node = DiagnosisNode(llm_diagnosis)
    shopping_search_node = ShoppingSearchNode(llm_tool_call, tavily_tool)
    explain_node = ExplainNode(llm)

    workflow = StateGraph(AgentState)
    workflow.add_node("thinking", thinking_node)
    workflow.add_node("general_chat", general_chat_node)
    workflow.add_node("diagnosis", diagnosis_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("shopping_search", shopping_search_node)
    workflow.add_node("explain", explain_node)

    workflow.set_entry_point("thinking")
    
    workflow.add_conditional_edges("thinking", lambda x: x['next_step'], 
        {
            "general_chat": "general_chat", 
            "diagnosis": "diagnosis", 
            "shopping_search": "shopping_search"
        })
    
    def route_interview(state):
        if state.get("diagnosis_progress"):
            return "diagnosis"
        if all([state.get("body_part"), state.get("symptoms"), state.get("duration"), state.get("allergies")]):
            return "diagnosis"
        return "diagnosis"
        
    workflow.add_conditional_edges("interview", route_interview, {
        "diagnosis": "diagnosis"
    })

    # Diagnosis Routing
    def route_diagnosis(state):
        if state.get("next_step") == "ask_question":
            return "interview"
        return "explain"

    workflow.add_conditional_edges("diagnosis", route_diagnosis, {
        "interview": "interview",
        "explain": "explain"
    })
    
    workflow.add_edge("general_chat", END)

    
    # Conditional routing for shopping intent
    def route_explain(state):
        if state.get("shopping_intent"):
            return "shopping_search"
        return END

    workflow.add_conditional_edges("explain", route_explain, {
        "shopping_search": "shopping_search",
        END: END
    })
    
    workflow.add_edge("shopping_search", END)

    return workflow.compile(checkpointer=checkpointer)
