import os
from langgraph.graph import StateGraph, END
from app.core.models import AgentState

# Import Nodes for 4b
from app.workflow.med_gemma_4b.nodes.thinking_node import ThinkingNode
from app.workflow.med_gemma_4b.nodes.general_chat_node import GeneralChatNode
from app.workflow.med_gemma_4b.nodes.shopping_search_node import ShoppingSearchNode
from app.workflow.med_gemma_4b.nodes.explain_node import ExplainNode
from app.workflow.med_gemma_4b.nodes.ask_treatment_node import AskTreatmentNode
# from app.workflow.med_gemma_4b.nodes.diagnosis.graph import build_diagnosis_subgraph
from app.workflow.diagnosis_4b.graph import build_diagnosis_subgraph

def build_graph(llm, llm_diagnosis, checkpointer, tavily_tool=None):
    # Initialize Nodes
    thinking_node = ThinkingNode(llm)
    general_chat_node = GeneralChatNode(llm)
    shopping_search_node = ShoppingSearchNode(llm, tavily_tool)
    explain_node = ExplainNode(llm)
    ask_treatment_node = AskTreatmentNode(llm)
    
    # Subgraph
    diagnosis_subgraph = build_diagnosis_subgraph(llm, llm_diagnosis)
    if not os.path.exists("output"):
        os.mkdir("output")
    try:
        image = diagnosis_subgraph.get_graph().draw_mermaid_png()
        with open("output/diagnosis_subgraph.png", "wb") as f:
            f.write(image)
    except Exception:
        pass

    workflow = StateGraph(AgentState)
    workflow.add_node("thinking", thinking_node)
    workflow.add_node("general_chat", general_chat_node)
    workflow.add_node("diagnosis_process", diagnosis_subgraph)
    workflow.add_node("shopping_search", shopping_search_node)
    workflow.add_node("explain", explain_node)
    workflow.add_node("ask_treatment", ask_treatment_node)

    workflow.set_entry_point("thinking")
    workflow.add_conditional_edges("thinking", lambda x: x['next_step'], 
        {
            "general_chat": "general_chat", 
            "diagnosis": "diagnosis_process", 
            "shopping_search": "shopping_search"
        })

    # workflow.add_edge("thinking", "routing")
    # workflow.add_conditional_edges("routing", lambda x: x['next_step'], 
    #     {
    #         "general_chat": "general_chat", 
    #         "diagnosis": "diagnosis_process", 
    #         "shopping_search": "shopping_search"
    #     })
    
    workflow.add_edge("diagnosis_process", "explain")
    workflow.add_edge("explain", "ask_treatment")
    workflow.add_edge("general_chat", END)

    # After ask_treatment: go to shopping_search if user confirmed, else END
    def route_after_ask_treatment(state):
        if state.get("shopping_intent"):
            return "shopping_search"
        return END

    workflow.add_conditional_edges("ask_treatment", route_after_ask_treatment, {
        "shopping_search": "shopping_search",
        END: END
    })
    
    workflow.add_edge("shopping_search", END)

    return workflow.compile(checkpointer=checkpointer)
