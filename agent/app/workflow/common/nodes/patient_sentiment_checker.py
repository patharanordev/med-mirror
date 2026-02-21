from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class PatientSentimentResult(BaseModel):
    is_negative: bool = Field(
        description=(
            "True if the user's reply is a negative, dismissive, or non-informative answer "
            "(e.g. 'no', 'none', 'I don't know', 'ไม่มี', 'ไม่รู้'). "
            "False if the reply contains any actual information."
        )
    )
    reasoning: str = Field(
        description="One short sentence explaining the classification."
    )


class PatientSentimentChecker:
    """
    LLM-based sentiment/intent checker shared across all workflows.

    Determines whether the user's reply in a medical screening context
    is a NEGATIVE answer (no info, refusal, don't know) vs. an answer
    that contains actual medical information.

    Used by:
    - EvaluationNode (diagnosis_4b): force-clear __MISSING__ fields on negative reply
    - AskTreatmentNode (med_gemma_4b): detect if user declines product recommendation
    """

    _SYSTEM_PROMPT = """\
<role>Medical Answer Sentiment Classifier</role>

<context>
  A medical screening assistant just asked the patient about one or more
  missing health details. The patient's reply is shown below.
</context>

<asked_fields>{asked_fields}</asked_fields>
<patient_reply>{user_answer}</patient_reply>

<task>
  Decide whether the patient's reply is NEGATIVE/NON-INFORMATIVE for the asked fields.

  A reply is NEGATIVE if it:
  - Explicitly denies or negates (e.g. "no", "none", "ไม่มี", "ไม่ได้")
  - Expresses ignorance (e.g. "I don't know", "ไม่รู้", "ไม่แน่ใจ")
  - Is entirely off-topic or a deflection that provides no medical data
  - Is a single-word brush-off (e.g. "okay", "fine", "ปกติ" with no detail)

  A reply is NOT NEGATIVE if it:
  - Contains any concrete medical detail, even briefly
  - Partially answers the question
  - Provides a quantity, duration, description, or qualifier
</task>

<output_instructions>
{format_instructions}
</output_instructions>"""

    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=PatientSentimentResult)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", self._SYSTEM_PROMPT)]
        ).partial(format_instructions=self.parser.get_format_instructions())
        self._chain = self.prompt | self.llm | self.parser

    async def is_negative(self, user_answer: str, asked_fields: list[str]) -> bool:
        """
        Returns True if the user's reply is a negative/non-informative answer
        for the given asked_fields. Falls back to False on any error.
        """
        try:
            result: PatientSentimentResult = await self._chain.ainvoke({
                "user_answer": user_answer,
                "asked_fields": ", ".join(asked_fields),
            })
            print(
                f"PatientSentimentChecker: is_negative={result.is_negative}, "
                f"reasoning={result.reasoning}"
            )
            return result.is_negative
        except Exception as e:
            print(f"PatientSentimentChecker error (defaulting to False): {e}")
            return False
