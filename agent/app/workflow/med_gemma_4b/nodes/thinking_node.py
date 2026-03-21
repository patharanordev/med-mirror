from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState

from app.prompts.thinking import get_system_message
from app.models.graph_states import ThinkingResultSimple

class ThinkingNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- THINKING NODE (4b - Lite) ---")
        
        from langchain_core.output_parsers import JsonOutputParser
        parser = JsonOutputParser(pydantic_object=ThinkingResultSimple)

        system_message = get_system_message()

        # Tell LangChain to interpret them using "jinja2" instead of the default
        # This allows you to use {{variable}} syntax inside your prompt string
        system_prompt = SystemMessagePromptTemplate.from_template(
            system_message.get('content'), 
            template_format="jinja2"
        )

        prompt = ChatPromptTemplate.from_messages([
            system_prompt,
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
