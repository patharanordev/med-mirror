
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.models import AgentState, DiagnosisResult
from langchain_core.output_parsers import JsonOutputParser
import json
import re

class DefiniteDiagnosisNode:
    def __init__(self, llm):
        self.llm = llm # Expected: medgemma-1.5:4b
        
    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS 4B: DEFINITE DIAGNOSIS NODE ---")
        
        # We assume we have all necessary info now (or as much as possible)
        parser = JsonOutputParser(pydantic_object=DiagnosisResult)
        
        system_msg = """
        ### ROLE
        You are an expert Dermatologist (MedMirror AI). 
        You have collected all necessary patient information.
        Now provide a DEFINITE DIAGNOSIS based on the evidence.
        
        IMPORTANT: You MUST answer in the user's language: {language}. 
        Do NOT provide translations or dual-language output.

        ### TASK
        1. Analyze the {context}.
        2. Provide the final identification of the disease/condition.
        3. Explain your reasoning briefly.
        4. Recommend next steps (treatment or consultation).

        ### OUTPUT JSON SCHEMA
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages"),
        ])
        
        progress_log = state.get("diagnosis_progress", [])
        language = state.get("language", "English")
        
        inputs = {
            "messages": state['messages'],
            "context": state.get("context", "No context"),
            "format_instructions": parser.get_format_instructions(),
            "language": language
        }
        
        try:
            chain = prompt | self.llm
            msg = await chain.ainvoke(inputs, config=config)
            raw_content = msg.content
            
            # Extract JSON and Thoughts (Reuse logic)
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*\})", raw_content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                diagnosis_thought = raw_content.replace(json_match.group(0), "").strip()
                result_dict = json.loads(json_str)
            else:
                result_dict = json.loads(raw_content)
                diagnosis_thought = "No separate thought process found."

            result = DiagnosisResult(**result_dict)
            
            # Update State
            new_progress = progress_log + [f"Final Diagnosis: {result.final_diagnosis}"]
            
            return {
                "diagnosis_thought_process": diagnosis_thought,
                "diagnosis": result.final_diagnosis,
                "diagnosis_confidence": result.confidence,
                "differential_diagnosis": result.differential_diagnosis,
                "diagnosis_progress": new_progress,
                "diagnosis_complete": True,
                "next_step": "explain" # We set this to signal completion to main graph
            }
                
        except Exception as e:
            print(f"Definite Diagnosis Error: {e}")
            return {
                "diagnosis": "Consult Doctor (Error Fallback)",
                "diagnosis_complete": True,
                "next_step": "explain"
            }
