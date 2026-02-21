from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState
from pydantic.v1 import BaseModel as BaseModelV1, Field as FieldV1
from typing import Literal

# Local model for 4b workflow (simpler, no todo)
class ThinkingResultSimple(BaseModelV1):
    analysis: str = FieldV1(description="Brief analysis of intent.")
    next_step: Literal['general_chat', 'diagnosis', 'shopping_search']

class RoutingNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- ROUTING NODE (4b) ---")
        
        from langchain_core.output_parsers import JsonOutputParser
        parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)
        
        thinking_process = state.get("thinking_process", "No detailed thought process available.")

        # System prompt explicitly asks to format the previous thought
        system_msg = """<role>JSON Formatting Assistant</role>

<goal>Take the provided ThinkingProcess and convert it into a valid JSON routing decision.</goal>

<routing_rules>
  - 'general_chat': Greetings, small talk, jokes, or non-medical questions.
  - 'diagnosis': User mentions a body part, symptom, condition, or problem.
  - 'shopping_search': User explicitly asks to BUY products.
</routing_rules>

<input>
  <thinking_process>{thinking_process}</thinking_process>
</input>

<output_format priority="CRITICAL">
  - Return ONLY a raw JSON object. No markdown, no explanation, no extra text.
  - Must match the schema exactly:
  {format_instructions}
</output_format>"""
        
        prompt = ChatPromptTemplate.from_template(system_msg)

        chain = (prompt | self.llm | parser).with_config(
            {"run_name": "RoutingChain"}
        )
        
        try:
            result_dict = await chain.ainvoke({
                "thinking_process": thinking_process,
                "format_instructions": parser.get_format_instructions()
            }, config=config)
            
            result = ThinkingResultSimple(**result_dict)
            return {"next_step": result.next_step}
        except Exception as e:
            print(f"Routing Error: {e}")
            # Fallback: simple keyword matching if JSON fails, or default to general_chat
            thought_lower = thinking_process.lower()
            if "diagnosis" in thought_lower or "symptom" in thought_lower or "pain" in thought_lower:
                 return {"next_step": "diagnosis"}
            if "buy" in thought_lower or "product" in thought_lower or "recommend" in thought_lower:
                 return {"next_step": "shopping_search"}
            return {"next_step": "general_chat"}
