import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.core.models import ChatRequest
from app.services.agent_graph import agent_service

router = APIRouter()

@router.get("/")
def health_check():
    return {"status": "Agent is running (Clean Arch)", "service": "MedMirror Agent"}


def create_multimodal_message(text: str, image: str = None) -> HumanMessage:
    """
    Create a HumanMessage with optional image content for multimodal models.
    Image should be a base64 data URL (e.g., 'data:image/jpeg;base64,...')
    """
    if image:
        # Multimodal message format for vision models
        content = [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {"url": image}
            }
        ]
        return HumanMessage(content=content)
    else:
        # Text-only message
        return HumanMessage(content=text)


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streaming endpoint for the medical agent with multimodal support.
    Accepts optional image (base64 data URL) for vision-based analysis.
    """
    
    # 1. Convert history to LangChain format
    messages = []
    if request.history:
        for msg in request.history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))
    
    # Add current message (with optional image for multimodal)
    current_message = create_multimodal_message(request.message, request.image)
    messages.append(current_message)
    
    # 2. Prepare Graph Input
    inputs = {
        "messages": messages,
        "context": request.context
    }

    # 3. Stream Generator
    async def event_generator():
        try:
            # Get the compiled graph from the service
            app_graph = agent_service.get_graph()
            
            # Stream the events from the graph
            async for event in app_graph.astream_events(inputs, version="v1"):
                kind = event["event"]
                
                # Filter for the token stream from the ChatModel
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
                        
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # Send error as a special event
            error_msg = json.dumps({"error": str(e)})
            yield f"data: {error_msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

