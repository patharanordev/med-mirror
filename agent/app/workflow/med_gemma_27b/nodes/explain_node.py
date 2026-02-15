from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState

class ExplainNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- EXPLAIN NODE ---")
        
        diagnosis = state.get("diagnosis", "Unclear Condition")
        is_critical = state.get("is_critical", False)
        diffs = state.get("differential_diagnosis", [])
        
        system_msg = settings.get_system_prompt() + f"""
        
        TASK: Explain the diagnosis to the patient.
        Dataset:
        - Diagnosis: {diagnosis}
        - Critical: {is_critical}
        - Possibilities: {diffs}
        
        Guidelines:
        1. If Critical: WARN user to see a doctor immediately. Be serious but calm.
        2. If Not Critical: Give a friendly explanation. Suggest general care 1-2 bullet points.
        3. Style: Concise, Smart, Witty (if not critical).
        4. Length: 2-3 sentences max.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages")
        ])
        
        inputs = {"messages": state['messages'],"context": state.get("context", "")}
        
        try:
            chain = (prompt | self.llm).with_config({"run_name": "ExplainChain"})
            response = await chain.ainvoke(inputs, config=config)
            return {"messages": [response]}
        except Exception as e:
            print(f"Explain Node Error: {e}")
            return {"messages": [AIMessage(content="I recommend seeing a doctor for a proper checkup.")]}
