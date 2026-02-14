import json
import io
import logging
import uuid
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.core.models import ChatRequest
from app.services.agent_graph import agent_service
from app.services.stt_service import stt_service
from langgraph.types import Command

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
        content = await file.read()
        logger.info(f"STT: Read {len(content)} bytes.")
        
        binary_file = io.BytesIO(content)
        text = stt_service.transcribe(binary_file)
        logger.info(f"STT: Transcription success: '{text}'")
        
        return {"text": text}
    except Exception as e:
        logger.error(f"STT: Transcription FAILED: {e}", exc_info=True)
        return {"error": str(e), "text": ""}

@router.post("/chat/{thread_id}")
async def chat_endpoint(request: ChatRequest, thread_id:str):
    """
    Streaming endpoint for the medical agent.
    """
    logger.info(f"CHAT: Received request with {len(request.history)} history messages.")
    
    # 1. Convert history to LangChain format
    messages = []
    
    logger.info(f"CHAT: Processing request. run_id in payload: {request.run_id}")
    
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
            app_graph = agent_service.get_graph()
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "run_id": str(uuid.uuid4())
                }
            }
            
            logger.info(f"CHAT: Starting astream for thread_id={thread_id}")
            
            # State tracking
            is_model_reasoning = False
            collected_content = {"thinking": [], "plan": [], "text": []}

            # Check for existing interrupts
            snapshot = await app_graph.aget_state(config)
            
            if snapshot.next and len(snapshot.tasks) > 0 and snapshot.tasks[0].interrupts:
                 # Resume from interrupt
                logger.info(f"CHAT: Resuming from interrupt for thread_id={thread_id}")
                # The user's message IS the answer/resume value
                # We use the raw message content as the resume value
                runner = app_graph.astream(
                    Command(resume={
                        "interrupt_response": request.message,
                        "run_id": request.run_id
                    }), 
                    config=config, 
                    stream_mode=["messages", "updates"]
                )
            else:
                # Start new run
                logger.info(f"CHAT: Starting new run for thread_id={thread_id}")
                runner = app_graph.astream(inputs, config=config, stream_mode=["messages", "updates"])

            async for chunk in runner:
                mode, data = chunk
                
                # --- MODE: MESSAGES (Tokens) ---
                if mode == "messages":
                    message_chunk, metadata = data
                    content = message_chunk.content
                    
                    if content:
                        # Simple reasoning tag detection
                        if "<think>" in content or "<unused94>" in content:
                            is_model_reasoning = True
                            # Notify UI that reasoning is starting if we just switched
                            yield f"data: {json.dumps({'type': 'task', 'content': 'Thinking...'})}\n\n"
                        
                        msg_type = "thinking" if is_model_reasoning else "text"
                        
                        if "</think>" in content or "<unused95>" in content:
                            is_model_reasoning = False
                            msg_type = "thinking"

                        collected_content[msg_type].append(content)
                        yield f"data: {json.dumps({'type': msg_type, 'content': content})}\n\n"
                    continue

                # --- MODE: UPDATES (State Changes & Interrupts) ---
                elif mode == "updates":
                    # Best Practice: Handle interrupts explicitly from the updates stream
                    interrupt = data.get("__interrupt__")
                    if interrupt:
                        interrupt, = interrupt

                        yield f"data: {json.dumps({'type': 'interrupt', 'content': interrupt.value})}\n\n"
                        continue
                    
                    # Handle Node Updates
                    # 1. Thinking Node - Extract Plan
                    if "thinking" in data:
                        output = data["thinking"]
                        plan = None
                        if output:
                            # Handle Pydantic V1 (.dict()) or plain dict or object attr
                            if hasattr(output, 'todo'):
                                plan = output.todo
                            elif isinstance(output, dict):
                                plan = output.get('todo')
                                if not plan and 'todo' in output: 
                                    plan = output['todo']
                        
                        if plan:
                             collected_content["plan"].append(json.dumps(plan))
                             yield f"data: {json.dumps({'type': 'task', 'content': plan})}\n\n"

                    # 2. Interview Node - Extract Profile
                    if "interview" in data:
                        output = data["interview"]
                        updates = {}
                        
                        data_src = output
                        if hasattr(output, 'dict'):
                             data_src = output.dict()
                        
                        if isinstance(data_src, dict):
                            for key in ["body_part", "duration", "symptoms", "allergies"]:
                                if data_src.get(key):
                                    updates[key] = data_src[key]

                        if updates:
                            yield f"data: {json.dumps({'type': 'profile_update', 'content': updates})}\n\n"

                    # 3. Shopping Node - Tool Search Completion (Inferred)
                    if "shopping_search" in data:
                        # If we get an update from shopping_search, it means the search/recommendation is done.
                        # We can't easily see "start" of tool in this mode, but we can confirm completion.
                         yield f"data: {json.dumps({'type': 'tool', 'content': 'Search Completed'})}\n\n"


            # --- FINAL OUTPUT ---
            debug_payload = {
                "thinking": "".join(collected_content["thinking"]),
                "plan": ", ".join(collected_content["plan"]),
                "text": "".join(collected_content["text"])
            }
            yield f"data: {json.dumps({'type': 'debug', 'content': json.dumps(debug_payload)})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"CHAT: Error in event_generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")