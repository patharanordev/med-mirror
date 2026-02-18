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
        user_language = state.get("language", "English")
        
        system_msg = f"""
        
        TASK: Explain the diagnosis to the patient.
        
        Definite diagnosis:
        <DefiniteDiagnosis>
        {diagnosis_text}
        </DefiniteDiagnosis>
        
        Guidelines:
        1. Language: Answer in {user_language}.
        2. Style: DIRECT, SMART, CONCISE.
           - NO greetings (e.g., "Hello", "How are you").
           - NO questions (e.g., "Do you have allergies?").
           - Start directly with the explanation.
        3. Content:
           - Explain the likely cause clearly.
           - Give specific, actionable advice (e.g., "Apply cool compress," "Avoid spicy food").
        4. Tone: Professional but approachable.
        5. Length: Keep it short (2-4 sentences). 
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
        ])
        
        inputs = {
            "context": state.get("context", ""),
        }
        
        try:
            chain = (prompt | self.llm).with_config({"run_name": "ExplainChain"})
            response = await chain.ainvoke(inputs, config=config)
            return {"messages": [response]}
        except Exception as e:
            print(f"Explain Node Error: {e}")
            return {"messages": [AIMessage(content="I recommend seeing a doctor for a proper checkup.")]}
