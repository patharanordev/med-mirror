from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class HITLInterest(BaseModel):
    is_interested: bool = Field(
        description=(
            "True if the user expresses interest, willingness, or openness to the offer "
            "(e.g. 'ดี', 'ได้', 'โอเค', 'yes', 'sure', 'show me'). "
            "False if the user declines, refuses, or shows no interest."
        )
    )
    reasoning: str = Field(description="One short sentence explaining the classification.")


class HITLInterestChecker:
    """
    LLM-based interest classifier for Human-In-The-Loop (HITL) nodes.

    Detects whether the patient is INTERESTED or NOT INTERESTED in an offer
    presented by the assistant (e.g. product recommendations, additional info).

    Prompt is language-aware: interprets Thai and English affirmatives/negatives
    in the context of the specific question asked.

    Used by:
    - AskTreatmentNode (med_gemma_4b): decide whether to show product recommendations
    """

    _SYSTEM_PROMPT = """\
<role>Patient Interest Classifier</role>

<language_instruction>
  The patient replied in {language}. Interpret their reply in that language context.
  Common affirmatives in Thai: "ดี", "ได้", "โอเค", "ใช่", "สนใจ", "เอา", "ดูเลย", "อยากดู"
  Common negatives in Thai: "ไม่", "ไม่สนใจ", "ไม่เอา", "ไม่ต้องการ", "ผ่าน", "ไม่ต้อง"
</language_instruction>

<context>
  The assistant just offered the patient something via a HITL question.
  <offer>{question_context}</offer>
</context>

<patient_reply>{user_answer}</patient_reply>

<task>
  Classify whether the patient IS INTERESTED or NOT INTERESTED in the offer.

  INTERESTED (is_interested=true):
  - Any affirmative, even minimal (e.g. "ดี", "ได้", "sure", "yes", "ok", "show me")
  - Curiosity or openness (e.g. "อยากดู", "น่าสนใจ", "why not")
  - If the intent is genuinely unclear, lean toward INTERESTED to avoid missing the patient's intent.

  NOT INTERESTED (is_interested=false):
  - Clear refusal (e.g. "ไม่", "no", "ไม่สนใจ", "pass", "ไม่ต้องการ", "ไม่ต้อง")
  - Redirecting away from the offer entirely
</task>

<output_instructions>
{format_instructions}
</output_instructions>"""

    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=HITLInterest)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", self._SYSTEM_PROMPT)]
        ).partial(format_instructions=self.parser.get_format_instructions())
        self._chain = self.prompt | self.llm | self.parser

    async def is_interested(
        self,
        user_answer: str,
        question_context: str,
        language: str = "Thai",
    ) -> bool:
        """
        Returns True if the patient is interested in the HITL offer.
        Respects the user's detected language.
        Falls back to True on any error (lean toward showing the offer).
        """
        try:
            result: HITLInterest = await self._chain.ainvoke({
                "user_answer": user_answer,
                "question_context": question_context,
                "language": language,
            })
            print(
                f"HITLInterestChecker: is_interested={result.is_interested}, "
                f"reasoning={result.reasoning}"
            )
            return result.is_interested
        except Exception as e:
            print(f"HITLInterestChecker error (defaulting to True): {e}")
            return True
