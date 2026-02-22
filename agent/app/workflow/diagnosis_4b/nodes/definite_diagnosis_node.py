from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState

class DefiniteDiagnosisNode:
    def __init__(self, llm):
        self.llm = llm # Expected: medgemma-1.5:4b
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: DEFINITE DIAGNOSIS NODE ---")
        
        system_msg = """
        ### ROLE
        You are an expert Dermatologist (MedMirror AI). 
        You have collected all necessary patient information.
        Now provide a DEFINITE DIAGNOSIS based on the evidence.
        
        IMPORTANT: You MUST answer in the user's language: {language}. 
        Do NOT provide translations or dual-language output.

        ### TASK
        1. Analyze this context:
        {context}


        2. Provide the final identification of the disease/condition.
        3. Explain your reasoning briefly.
        4. Recommend next steps (treatment or consultation).

        ### OUTPUT FORMAT
        - Standard text or Markdown.
        - Be professional, empathetic, and clear.
        - Structure your answer with clear headings if necessary.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
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
            
            # Allow streaming, add tag for routes.py to classify it as 'thinking'
            config_streaming = config.copy()
            config_streaming["tags"] = ["definite_diagnosis"]
            
            msg = await chain.ainvoke(inputs, config=config_streaming)
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
