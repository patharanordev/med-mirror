from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState, DiagnosisResult

class DiagnosisNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- DIAGNOSIS NODE (ITERATIVE) ---")
        
        from langchain_core.output_parsers import JsonOutputParser
        parser = JsonOutputParser(pydantic_object=DiagnosisResult)
        
        system_msg = """
        ### ROLE
        You are an expert Dermatologist (MedMirror AI). You do not jump to conclusions. You use the "Socratic Method" to rule out differential diagnoses.
        IMPORTANT: You MUST answer in the user's language: {language}. 
        Do NOT provide translations or dual-language output. Also do NOT output in a different language than {language}.

        ### DIAGNOSTIC PHILOSOPHY
        A symptom like "dark circles" (ขอบตาดำ) is not a diagnosis; it is a sign. You must investigate:
        1. Lifestyle (Sleep/Stress)
        2. Genetics/Anatomy
        3. Medical: Allergic Shiners (Atopy/Rhinitis)
        4. Post-Inflammatory Hyperpigmentation

        ### STEP 1: DIFFERENTIAL ANALYSIS
        - Based on the current {context}, list the 3 most likely causes.
        - For each cause, identify if you have enough evidence to "Rule In" or "Rule Out".
        - Example: To rule out Allergies, you MUST know about nighttime coughing/sneezing.

        ### STEP 2: AUDIT & GATHER
        You are STRICTLY FORBIDDEN from choosing 'explain' unless you have data for:
        1. Duration (How long?)
        2. Systemic Symptoms (Itching eyes, sneezing, nighttime cough?)
        3. Triggers/Diet (New products, food habits?)
        4. Sleep Quality (Is it just lack of sleep or something else?)

        ### STEP 3: DECISION LOGIC
        - SET next_step = 'ask_question' IF:
            - You have only 1-2 pieces of information.
            - You haven't ruled out systemic causes (like allergies/ภูมิแพ้).
            - Your 'confidence' is below 0.95.
        - SET next_step = 'explain' ONLY IF:
            - You have investigated at least 3 distinct categories of information.
            - 'is_critical' is True.

        ### OUTPUT JSON SCHEMA
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder("messages"),
        ])
        
        
        # Prepare Input
        progress_log = state.get("diagnosis_progress", [])
        language = state.get("language", "English")
        inputs = {
            "messages": state['messages'],
            "context": state.get("context", "No context"),
            "diagnosis_progress": "\n".join(progress_log) if progress_log else "None",
            "format_instructions": parser.get_format_instructions(),
            "language": language
        }
        
        try:
            # Invoking LLM directly to get raw output (thoughts + JSON)
            chain = (prompt | self.llm).with_config({"run_name": "DiagnosisChain"})
            msg = await chain.ainvoke(inputs, config=config)
            raw_content = msg.content
            
            # Extract JSON and Thoughts
            import re
            import json
            
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*\})", raw_content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                diagnosis_thought = raw_content.replace(json_match.group(0), "").strip()
                result_dict = json.loads(json_str)
            else:
                # Fallback: Try to parse the whole thing if it looks like JSON, or treat as error
                try:
                    result_dict = json.loads(raw_content)
                    diagnosis_thought = "No separate thought process found."
                except:
                     print(f"Failed to parse JSON from: {raw_content[:100]}...")
                     raise ValueError("Could not extract JSON from response")

            result = DiagnosisResult(**result_dict)
            
            # Update State
            new_progress = progress_log + [f"Analysis: {result.reasoning} -> Diffs: {result.differential_diagnosis}"]
            
            common_output = {
                "diagnosis_thought_process": diagnosis_thought,
                "differential_diagnosis": result.differential_diagnosis,
                "diagnosis_confidence": result.confidence,
                "diagnosis_progress": new_progress
            }

            if result.next_step == 'ask_question':
                return {
                    **common_output,
                    "next_step": "ask_question",
                    "diagnostic_question": result.question,
                }
            else:
                return {
                    **common_output,
                    "next_step": "explain",
                    "diagnosis": result.final_diagnosis,
                    "is_critical": result.is_critical,
                }
                
        except Exception as e:
            print(f"Diagnosis Node Error: {e}")
            # Fallback to explain if something breaks
            return {"next_step": "explain", "diagnosis": "Consult Doctor (Error Fallback)"}
