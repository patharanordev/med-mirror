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
        
        # Now using raw text diagnosis
        diagnosis_text = state.get("definite_diagnosis", "No diagnosis available.")
        
        system_msg = settings.get_system_prompt() + f"""
        
        TASK: Explain the diagnosis to the patient.
        
        The Dermatologist AI has provided this diagnosis:
        <DiagnosisResults>
        {diagnosis_text}
        </DiagnosisResults>
        
        Guidelines:
        1. Summarize the diagnosis for the patient.
        2. Be empathetic and clear.
        3. If the diagnosis mentions critical conditions, WARN the user to see a doctor.
        4. If not critical, provide self-care advice and do NOT recommend a doctor unless necessary.
        5. Style: Concise, Smart, Witty (if appropriate).
        6. Length: 2-3 sentences max.
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
