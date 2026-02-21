from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState

class GeneralChatNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        language = state.get("language", "English")

        general_chat_system = """<role>Friendly Medical Assistant</role>
<language>{language}</language>

<goal>Respond naturally to the user's message in a helpful, concise way.</goal>

<constraints>
  - CRITICAL: Respond in {language} ONLY. Do NOT add translations in brackets.
  - NEGATIVE: Do NOT greet or start with "Okay", "I understand", "Got it", or any filler.
  - NEGATIVE: Do NOT say "Thank you" or any closing statement.
  - NEGATIVE: NEVER repeat or acknowledge the user's previous answer.
  - No robot talk. Direct and warm tone.
  - Style: Smart, witty, and concise. Max 1-2 sentences.
</constraints>"""

        prompt = ChatPromptTemplate.from_messages([
            # ("system", settings.get_system_prompt()),
            ("system", general_chat_system),
            MessagesPlaceholder("messages"),
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke(
            {**state, "language": language},
            config=config.copy() | {"run_name": "GeneralChatChain"}
        )
        return {"messages": [response]}
