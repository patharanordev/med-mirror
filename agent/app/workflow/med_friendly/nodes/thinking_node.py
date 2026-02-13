from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, ThinkingResult

class ThinkingNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- THINKING NODE ---")
        
        # 1. System Prompt for Routing
        system_msg = """You are the 'Brain' of MedMirror. 
        Decide the next step based on the user's input.
        
        Routing Rules:
        - 'general_chat': Greetings, small talk, jokes, or non-medical questions.
        - 'interview': User mentions a body part, symptom, or problem (e.g., "my face is red", "panda eyes").
        - 'shopping_search': User explicitly asks to BUY products or RECOMENDATIONS for products.
        - 'diagnosis': (Rarely used directly) Only if ALL info (symptoms, duration, allergies) is present.
        
        Task: Generate a 'todo' list with 2-5 specific steps for the next stage (e.g., "Ask about duration", "Check for allergies", "Analyze symptom severity").

        Context: {context}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages"),
        ])

        # .with_structured_output(ThinkingResult) returns a Pydantic object
        chain = (prompt | self.llm.with_structured_output(ThinkingResult)).with_config(
            {"run_name": "ThinkingChain"}
        )
        
        try:
            # Inject context into state for the thinking node
            input_state = {**state, "context": state.get("context", "No context")}
            result = await chain.ainvoke(input_state, config=config)
            return {"todo": result.todo, "next_step": result.next_step}
        except Exception as e:
            # Fallback logic
            print(f"Thinking Error: {e}")
            return {"next_step": "general_chat"}
