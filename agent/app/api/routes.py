import json
import io
import logging
import uuid
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from langchain_core.messages import HumanMessage, AIMessage
import httpx

from app.core.config import settings
from app.core.models import ChatRequest, PatientInfo
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
@router.get("/proxy-image")
async def proxy_image(url: str = Query(...)):
    """
    Proxy external images to bypass CORS.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            return Response(
                content=resp.content, 
                media_type=resp.headers.get("content-type", "image/jpeg")
            )
    except Exception as e:
        logger.error(f"Image Proxy failed for {url}: {e}")
        return Response(status_code=404)

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
    # Check if state exists for this thread
    app_graph = agent_service.get_graph()
    config = {
        "configurable": {
            "thread_id": thread_id,
            "run_id": str(uuid.uuid4())
        }
    }

    # Fetch current state
    current_state = await app_graph.aget_state(config)
    state_exists = bool(current_state.values)

    if state_exists:
        logger.info(f"CHAT: State exists for {thread_id}. Ignoring client history to prevent duplication.")
        # Only pass the new message
        inputs = {
            "messages": [HumanMessage(content=request.message)],
            "context": request.context,
            "image_url": request.image_url
        }
    else:
        logger.info(f"CHAT: No state for {thread_id}. Hydrating from client history.")
        inputs = {
            "messages": messages, # Full history + current message
            "context": request.context,
            "image_url": request.image_url
        }

    # 3. Stream Generator
    async def event_generator():
        try:
            # app_graph and config are already defined in outer scope
            
            logger.info(f"CHAT: Starting astream for thread_id={thread_id}")
            
            # State tracking
            is_model_reasoning = False
            collected_content = {"thinking": [], "plan": [], "text": [], "decision": []}

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
                
                if mode == "messages":
                    message_chunk, metadata = data
                    content = message_chunk.content
                    
                    if content:
                        # Determine message type based on Node
                        node_name = metadata.get("langgraph_node")
                        
                        # Default to 'text' (visible in chat)
                        msg_type = "text"
                        
                        # Debug logging to identify node names and tags
                        logger.info(f"CHAT MSG: Node={node_name}, Tags={metadata.get('tags')}")

                        # Nodes that should NOT appear in chat bubble
                        if node_name in ["thinking", "routing", "definite_diagnosis", "diagnosis_process"]:
                            msg_type = "thinking"
                        
                        # Check tags for definite_diagnosis (since it's in a subgraph)
                        tags = metadata.get("tags", [])
                        if "definite_diagnosis" in tags:
                            msg_type = "thinking"
                        elif node_name in ["asker", "evaluation", "ask_treatment"]:
                            msg_type = "decision"
                            
                        # Also check for reasoning tags (DeepSeek style) just in case
                        if "<think>" in content or "<unused94>" in content:
                            is_model_reasoning = True
                            # Notify UI start of reasoning
                            yield f"data: {json.dumps({'type': 'task', 'content': 'Thinking...'})}\n\n"
                        
                        if is_model_reasoning:
                            msg_type = "thinking"  # Hide reasoning content
                            
                        if "</think>" in content or "<unused95>" in content:
                            is_model_reasoning = False
                        
                        collected_content[msg_type].append(content) if msg_type in collected_content else None
                        print(f"CHAT: {msg_type}: {content}")
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
                            # Use PatientInfo fields dynamically
                            for key in PatientInfo.__fields__.keys():
                                val = data_src.get(key)
                                if val and val != "__MISSING__":
                                    updates[key] = val

                        if updates:
                            yield f"data: {json.dumps({'type': 'profile_update', 'content': updates})}\n\n"

                    # 3. Shopping Node - Emit raw search results to client
                    if "shopping_search" in data:
                        output = data["shopping_search"]
                        if isinstance(output, dict):
                            # Process messages as text
                            messages = output.get("messages", [])
                            for msg in messages:
                                content = getattr(msg, 'content', str(msg))
                                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
                            
                            # Process search results
                            results = output.get("search_results", [])
                            if results:
                                yield f"data: {json.dumps({'type': 'search_result', 'content': results})}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'tool', 'content': 'Search Completed'})}\n\n"


            # --- FINAL OUTPUT ---
            debug_payload = {
                "thinking": "".join(collected_content["thinking"]),
                "plan": ", ".join(collected_content["plan"]),
                "text": "".join(collected_content["text"]),
                "decision": "".join(collected_content["decision"])
            }
            yield f"data: {json.dumps({'type': 'debug', 'content': json.dumps(debug_payload)})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"CHAT: Error in event_generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")