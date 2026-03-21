from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState
from app.prompts.definite_diagnosis import get_system_message

class DefiniteDiagnosisNode:
    def __init__(self, llm):
        self.llm = llm # Expected: medgemma-1.5:4b
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: DEFINITE DIAGNOSIS NODE ---")
        
        system_message = get_system_message()
        system_prompt = SystemMessagePromptTemplate.from_template(
            system_message.get('content'), 
            template_format="jinja2"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            system_prompt,
            MessagesPlaceholder("messages"),
        ])
        
        language = state.get("language", "English")
        
        inputs = {
            "messages": state['messages'],
            "context": state.get("context", "No context"),
            "language": language
        }
        

        try:
            chain = prompt | self.llm
            
            # Explicitly drop callbacks to prevent streaming tokens to the frontend
            config_silent = config.copy()
            if "callbacks" in config_silent:
                del config_silent["callbacks"]
                
             # Add tag just in case for other tools
            config_silent["tags"] = ["definite_diagnosis"]
            
            msg = await chain.ainvoke(inputs, config=config_silent)
            raw_content = msg.content
            
            # Simply store the raw content as the definite diagnosis
            # No parsing needed as per user request
            
            return {
                "definite_diagnosis": raw_content,
                "diagnosis_complete": True,
                "next_step": "explain" # We set this to signal completion to main graph
            }
                
        except Exception as e:
            print(f"Definite Diagnosis Error: {e}")
            return {
                "definite_diagnosis": "Error in diagnosis generation. improved context might be needed.",
                "diagnosis_complete": True,
                "next_step": "explain"
            }
