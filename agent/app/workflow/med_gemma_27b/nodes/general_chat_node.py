from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.core.models import AgentState

class GeneralChatNode:
    def __init__(self, llm):
        self.llm = llm

    async def __call__(self, state: AgentState, config: RunnableConfig):
        prompt = ChatPromptTemplate.from_messages([
            ("system", settings.get_system_prompt()),
            ("system", "Keep it short (1-2 sentences). Be smart & witty."),
            MessagesPlaceholder("messages"),
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke(state, config=config.copy() | {"run_name": "GeneralChatChain"})
        return {"messages": [response]}
