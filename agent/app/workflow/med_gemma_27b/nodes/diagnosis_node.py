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
        inputs = {
            "messages": state['messages'],
            "context": state.get("context", "No context"),
            "diagnosis_progress": "\n".join(progress_log) if progress_log else "None",
            "format_instructions": parser.get_format_instructions()
        }
        
        try:
            # structured output via JSON mode/prompt engineering
            # medgemma might not support function calling, so we use direct prompting
            chain = (prompt | self.llm | parser).with_config({"run_name": "DiagnosisChain"})
            result_dict = await chain.ainvoke(inputs, config=config)
            result = DiagnosisResult(**result_dict)
            
            # Update State
            new_progress = progress_log + [f"Analysis: {result.reasoning} -> Diffs: {result.differential_diagnosis}"]
            
            if result.next_step == 'ask_question':
                # We return the question as a message to be shown to the user
                return {
                    "next_step": "ask_question",
                    "diagnostic_question": result.question,
                    "differential_diagnosis": result.differential_diagnosis,
                    "diagnosis_confidence": result.confidence,
                    "diagnosis_progress": new_progress
                    # Messages will be handled by InterviewNode
                }
            else:
                # We are ready to explain
                return {
                    "next_step": "explain",
                    "diagnosis": result.final_diagnosis,
                    "is_critical": result.is_critical,
                    "differential_diagnosis": result.differential_diagnosis,
                    "diagnosis_confidence": result.confidence,
                    "diagnosis_progress": new_progress
                }
                
        except Exception as e:
            print(f"Diagnosis Node Error: {e}")
            # Fallback to explain if something breaks
            return {"next_step": "explain", "diagnosis": "Consult Doctor (Error Fallback)"}
