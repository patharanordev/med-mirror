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
        
        system_msg = f"""<role>Medical Explainer</role>
<language>{user_language}</language>

<goal>Explain the diagnosis clearly and directly to the patient.</goal>

<diagnosis>
{diagnosis_text}
</diagnosis>

<task>
  1. Read the diagnosis above.
  2. Explain the likely cause in simple, clear terms.
  3. Give 1-2 specific, actionable self-care tips (e.g., "Apply cool compress", "Avoid spicy food").
</task>

<constraints>
  - CRITICAL: Respond in {user_language} ONLY. Do NOT add translations in brackets.
  - NEGATIVE: Do NOT greet the user (no "Hello", "Hi", "How are you").
  - NEGATIVE: Do NOT ask the user any questions.
  - NEGATIVE: Do NOT start with "Okay", "I understand", "Got it", or any filler phrase.
  - NEGATIVE: Do NOT say "Thank you" or any closing statement.
  - NEGATIVE: Do NOT recommend a doctor visit unless it is a critical emergency.
  - Start the explanation IMMEDIATELY.
  - Tone: Professional but approachable.
  - Length: 2-4 sentences max.
</constraints>"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
        ])
        
        inputs = {
            "context": state.get("context", ""),
        }
        
        try:
            chain = (prompt | self.llm).with_config({"run_name": "ExplainChain"})
            response = await chain.ainvoke(inputs, config=config)
            return {"messages": [response], "explanation": response.content}
        except Exception as e:
            print(f"Explain Node Error: {e}")
            msg = AIMessage(content="I recommend seeing a doctor for a proper checkup.")
            return {"messages": [msg], "explanation": msg.content}
