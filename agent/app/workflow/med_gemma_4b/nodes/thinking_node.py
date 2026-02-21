from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState
from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1
from typing import Literal

# Local model for 4b workflow (simpler, no todo)
class ThinkingResultSimple(BaseModelV1):
    analysis: str = FieldV1(description="Brief analysis of intent.")
    next_step: Literal['general_chat', 'diagnosis', 'shopping_search']
    language: str = FieldV1(description="Detected language of the user (e.g., 'English', 'Thai', 'Japanese'). Default to 'English'.")
    shopping_intent: bool = FieldV1(default=False, description="True if user explicitly asks for products, medicine, cream, or treatment.")

class ThinkingNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- THINKING NODE (4b - Lite) ---")
        
        system_msg = """<role>MedMirror Brain — Intent Analyzer</role>

<goal>Analyze the user's input to decide the next step, detect their language, and identify shopping intent.</goal>

<routing_rules>
  - 'general_chat': Greetings, small talk, jokes, or non-medical questions.
  - 'diagnosis': User mentions a body part, symptom, condition, or problem (e.g., "my face is red", "panda eyes"). Route here even if info is incomplete.
  - 'shopping_search': User explicitly asks to BUY products or requests product recommendations.
</routing_rules>

<task>
  1. Analyze the user's message and intent.
  2. Detect the user's language (e.g., Thai, English, Chinese, Japanese, etc.).
  3. Detect 'shopping_intent': Set to True if user asks for medicine, products, cream, or treatment — even if routing to 'diagnosis'.
  4. Briefly state the reasoning for the chosen next_step.
</task>

<context>{context}</context>"""

        from langchain_core.output_parsers import JsonOutputParser
        parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("system", "<output_format priority=\"CRITICAL\">Return ONLY raw JSON. No markdown. Schema: {format_instructions}</output_format>"),
            MessagesPlaceholder("messages"),
        ])

        chain = (prompt | self.llm | parser).with_config(
            {"run_name": "ThinkingChain"}
        )
        
        try:
            # Inject context into state
            input_state = {
                **state, 
                "context": state.get("context", "No context"),
                "format_instructions": parser.get_format_instructions()
            }
            result_dict = await chain.ainvoke(input_state, config=config)
            
            # result_dict should match ThinkingResultSimple
            return {
                "thinking_process": result_dict.get("analysis", ""),
                "next_step": result_dict.get("next_step", "general_chat"),
                "language": result_dict.get("language", "English"),
                "shopping_intent": result_dict.get("shopping_intent", False)
            }
        except Exception as e:
            # Fallback logic
            print(f"Thinking Error: {e}")
            return {
                "thinking_process": "Error in thinking process.",
                "next_step": "general_chat",
                "language": "English"
            }
