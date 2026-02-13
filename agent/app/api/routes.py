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
            app_graph = agent_service.get_graph()
            thread_id = request.thread_id or str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            
            logger.info(f"CHAT: Starting astream_events for thread_id={thread_id}")
            
            # State tracking
            active_chain = None
            is_model_reasoning = False
            collected_content = {"thinking": [], "plan": [], "text": [], "tool": []}
        
            known_chains = [
                "ThinkingChain",
                "GeneralChatChain",
                "InterviewExtractionChain",
                "InterviewAskChain",
                "DiagnosisChain",
                "ShoppingProposalChain",
                "ShoppingSummarizeChain"
            ]

            async for event in app_graph.astream_events(inputs, config=config, version="v1"):
                kind = event["event"]
                name = event.get("name")
                tags = event.get("tags", [])

                # --- 1. HANDLE CHAIN START ---
                if kind == "on_chain_start" and name in known_chains:
                    active_chain = name
                    
                    # Notify UI that reasoning is starting
                    if name == "ThinkingChain":
                        yield f"data: {json.dumps({'type': 'task', 'content': 'Analyzing request...'})}\n\n"
                    continue # Skip to next event

                # --- 2. HANDLE INNER EVENTS FOR ACTIVE CHAINS ---
                
                # A. Thinking Chain Logic
                if active_chain == "ThinkingChain":
                    if kind in ["on_chat_model_stream", "on_llm_stream"]:
                        chunk = event["data"].get("chunk")
                        content = chunk.content if chunk else ""
                        
                        if content:
                            if any(tag in content for tag in ["<think>", "<unused94>"]):
                                is_model_reasoning = True
                            
                            if any(tag in content for tag in ["</think>", "<unused95>"]):
                                is_model_reasoning = False
                                yield f"data: {json.dumps({'type': 'thinking', 'content': content})}\n\n"
                                continue

                            # Stream reasoning tokens; hide raw JSON
                            if is_model_reasoning:
                                collected_content["thinking"].append(content)
                                yield f"data: {json.dumps({'type': 'thinking', 'content': content})}\n\n"
                        continue 

                    # Completion of ThinkingChain
                    if kind == "on_chain_end" and name == "ThinkingChain":
                        output = event["data"].get("output")
                        plan = None
                        
                        if output:
                            if hasattr(output, 'todo'):
                                plan = output.todo
                            elif isinstance(output, dict) and 'todo' in output:
                                plan = output['todo']
                        
                        if plan:
                            collected_content["plan"].append(json.dumps(plan))
                            yield f"data: {json.dumps({'type': 'task', 'content': plan})}\n\n"
                        
                        active_chain = None # Reset chain status
                    continue

                # B. Suppression Logic for internal extractions
                if active_chain == "InterviewExtractionChain":
                    if kind == "on_chain_end" and name == "InterviewExtractionChain":
                        active_chain = None
                    continue

                # --- 3. HANDLE CHAIN END FOR ALL OTHER CHAINS ---
                if kind == "on_chain_end" and name in known_chains:
                    active_chain = None
                    continue
                
                # --- 4. TOOL UPDATES ---
                if "tool_search" in tags:
                    if kind == "on_tool_start":
                        yield f"data: {json.dumps({'type': 'tool', 'content': 'Searching...'})}\n\n"
                        continue
                    elif kind == "on_tool_end":
                        yield f"data: {json.dumps({'type': 'tool', 'content': 'Search Completed'})}\n\n"
                        continue

                # --- 5. DEFAULT TEXT STREAMING ---
                if kind in ["on_chat_model_stream", "on_llm_stream"]:
                    chunk = event["data"].get("chunk")
                    content = chunk.content if chunk else ""
                    
                    if content:
                        if any(tag in content for tag in ["<think>", "<unused94>"]):
                            is_model_reasoning = True
                        
                        msg_type = "thinking" if is_model_reasoning else "text"
                        
                        if any(tag in content for tag in ["</think>", "<unused95>"]):
                            is_model_reasoning = False
                            msg_type = "thinking" 

                        collected_content[msg_type].append(content)
                        yield f"data: {json.dumps({'type': msg_type, 'content': content})}\n\n"

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