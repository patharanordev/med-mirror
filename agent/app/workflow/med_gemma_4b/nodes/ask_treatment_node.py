from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from app.core.models import AgentState
from app.workflow.common.nodes.hitl_interest_checker import HITLInterestChecker



class AskTreatmentNode:
    """
    HITL node: asks the user whether they would like to see
    recommended topical treatment products.

    - Uses the LLM to generate the question in the user's detected language.
    - Interrupts execution and waits for the user's answer.
    - Uses PydanticOutputParser to interpret the answer as structured data (no tool calling).
    - If the user agrees  → routes downstream to 'shopping_search'.
    - If the user declines → routes to END.

    The routing decision is stored in `shopping_intent` (bool) so that
    the existing `route_after_ask_treatment` conditional edge can re-use it.
    """

    def __init__(self, llm):
        self.llm = llm
        self.interest_checker = HITLInterestChecker(llm)

        # --- Prompt 1: Generate the question in user's language ---
        question_system = """\
<role>Empathetic Medical Assistant</role>
<language>{language}</language>

<goal>Ask the patient whether they would like to see recommended topical treatment products for their condition.</goal>

<context>
The patient recently received this medical explanation:
{explanation}
</context>

<task>
  Ask ONE short, natural question that invites the patient to say whether they want product recommendations based on their diagnosis.
  The question must fit naturally into a medical conversation — warm but not robotic.
</task>

<constraints>
  - CRITICAL: Ask in {language} ONLY. Do NOT add translations in brackets.
  - CRITICAL: You MUST end with a question mark (?).
  - NEGATIVE: Do NOT start with "Okay", "I understand", "Got it", "Sure", or any filler phrase.
  - NEGATIVE: Do NOT say "Thank you" or any closing statement.
  - NEGATIVE: NEVER repeat or acknowledge the user's previous answer.
  - No robot talk. Direct and warm tone.
  - Style: Concise, connected, and smart. Max 20 words.
  - Output ONLY the question — no extra text, no explanations.
</constraints>"""
        self.question_prompt = ChatPromptTemplate.from_messages([("system", question_system)])


    async def __call__(self, state: AgentState, config: RunnableConfig):
        print("--- ASK TREATMENT NODE (HITL) ---")

        user_language = state.get("language", "English")
        explanation = state.get("explanation", "No explanation provided.")

        # --- Step 1: Generate the question via LLM in the user's detected language ---
        try:
            chain = (self.question_prompt | self.llm).with_config({"run_name": "AskTreatmentChain"})
            response = await chain.ainvoke({"language": user_language, "explanation": explanation}, config=config)
            question = response.content.strip()
        except Exception as e:
            print(f"AskTreatmentNode question generation error: {e}")
            question = "Would you like to see recommended topical treatment products for your condition? (Yes / No)"

        user_answer = interrupt(question)

        if isinstance(user_answer, dict) and "interrupt_response" in user_answer:
            user_answer = user_answer["interrupt_response"]

        # --- Step 2: Detect interest via HITL-specific PatientSentimentChecker ---
        wants_products = True  # default affirmative (lean toward showing products)
        try:
            wants_products = await self.interest_checker.is_interested(
                user_answer=str(user_answer),
                question_context=question,
                language=user_language,
            )
            print(f"AskTreatmentNode: wants_products={wants_products}")
        except Exception as e:
            print(f"AskTreatmentNode interpretation error: {e}")


        return {
            "messages": [
                AIMessage(content=question),
                HumanMessage(content=str(user_answer)),
            ],
            "shopping_intent": wants_products,
        }
