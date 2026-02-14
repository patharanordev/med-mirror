from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt, Command
from app.core.config import settings
from app.core.models import AgentState, MedicalExtraction, QuestionResult

class InterviewNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        last_message = state['messages'][-1].content
             
        duration_interrupt = interrupt({
            "question": "How long has this been going on?",
            "run_id": config.get('configurable').get('run_id')
        })

        duration = duration_interrupt.get("interrupt_response")
        state["messages"].append(HumanMessage(content=f"duration: {duration}"))

        return Command(
            goto="diagnosis",
            update={
                "duration": duration,
                "symptoms": "",
                "body_part": "",
                "allergies": "",
                "messages": [
                    AIMessage(content="How long has this been going on?"), 
                    HumanMessage(content=duration)
                ]
            },
        )
