import json
import io
import logging
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.core.models import ChatRequest
from app.services.agent_graph import agent_service
from app.services.stt_service import stt_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
@router.get("/health")
async def root():
    return {
        "status": "ok",
        "stt_ready": stt_service.is_ready,
        "llm_ready": agent_service.is_ready,
        "llm_model": settings.LLM_MODEL
    }

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Local Whisper STT Endpoint.
    Accepts audio file, returns text.
    """
    try:
        logger.info(f"STT: Received file upload: {file.filename}")
        
        # Read file into memory (safe for faster-whisper)
        content = await file.read()
        logger.info(f"STT: Read {len(content)} bytes.")
        
        binary_file = io.BytesIO(content)
        
        text = stt_service.transcribe(binary_file)
        logger.info(f"STT: Transcription success: '{text}'")
        
        return {"text": text}
    except Exception as e:
        logger.error(f"STT: Transcription FAILED: {e}", exc_info=True)
        return {"error": str(e), "text": ""}

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streaming endpoint for the medical agent.
    """
    logger.info(f"CHAT: Received request with {len(request.history)} history messages.")
    
    # 1. Convert history to LangChain format
    messages = []
    if request.history:
        for msg in request.history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))
    
    # Add current message
    messages.append(HumanMessage(content=request.message))
    
    # 2. Prepare Graph Input
    inputs = {
        "messages": messages,
        "context": request.context,
        "image_url": request.image_url
    }

    # 3. Stream Generator
    async def event_generator():
        try:
            # Get the compiled graph from the service
            app_graph = agent_service.get_graph()
            
            # Configure thread_id for persistence
            import uuid
            thread_id = request.thread_id or str(uuid.uuid4())
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # Stream the events from the graph
            has_streamed = False
            logger.info(f"CHAT: Starting astream_events for thread_id={thread_id}")
            
            async for event in app_graph.astream_events(inputs, config=config, version="v1"):
                kind = event["event"]
                name = event.get("name", "Unknown")
                logger.info(f"CHAT: Event: {kind} | Name: {name}")
                
                # Filter for the token stream from the ChatModel or LLM
                if kind in ["on_chat_model_stream", "on_llm_stream"]:
                    data = event["data"]
                    chunk = data.get("chunk")
                    content = chunk.content if chunk else ""
                    
                    if content:
                        # logger.info(f"CHAT: Stream Content: {content[:20]}...") 
                        has_streamed = True
                        yield f"data: {json.dumps({'content': content})}\n\n"
                
                # Fallback: If no streaming happened, catch the final output
                elif kind == "on_chat_model_end" and not has_streamed:
                     logger.info("CHAT: Caught on_chat_model_end")
                     output = event["data"].get("output")
                     if output and hasattr(output, "generations"):
                         # Standard ChatResult structure
                         text = output.generations[0][0].text
                         if text:
                             logger.info(f"CHAT: Fallback Content: {text[:50]}...")
                             yield f"data: {json.dumps({'content': text})}\n\n"
                             has_streamed = True

            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # Send error as a special event
            logger.error(f"CHAT: Error in event_generator: {e}", exc_info=True)
            error_msg = json.dumps({"error": str(e)})
            yield f"data: {error_msg}\n\n"

            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # Send error as a special event
            error_msg = json.dumps({"error": str(e)})
            yield f"data: {error_msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
