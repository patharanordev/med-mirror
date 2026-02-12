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
            
            # State tracking# State tracking
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

                # 1. Handle START of ThinkingChain
                # if kind == "on_chain_start" and name == "ThinkingChain":
                #     active_chain = "ThinkingChain"
                #     yield f"data: {json.dumps({'type': 'task', 'content': 'Analyzing request...'})}\n\n"
                #     continue

                # 2. Handle specific logic WHILE ThinkingChain is active
                if active_chain == "ThinkingChain":
                    # Suppress tokens from leaking into 'text'
                    if kind in ["on_chat_model_stream", "on_llm_stream"]:
                        data = event["data"]
                        chunk = data.get("chunk")
                        if chunk and chunk.content:
                            collected_content["thinking"].append(chunk.content)
                        continue 

                    # 3. Handle END of ThinkingChain (Do this BEFORE resetting active_chain)
                    if kind == "on_chain_end" and name == "ThinkingChain":
                        active_chain = None # Reset here specifically
                        output = event["data"].get("output")
                        
                        # Robust extraction of the 'todo' list
                        plan = None
                        if output:
                            if hasattr(output, 'todo'): # Check if it's a Pydantic object
                                plan = output.todo
                            elif isinstance(output, dict) and 'todo' in output: # Check if it's a dict
                                plan = output['todo']
                        
                        if plan:
                            # Yield as 'todo' type as requested
                            yield f"data: {json.dumps({'type': 'task', 'content': plan})}\n\n"
                        continue

                # 4. General tracker for other chains (Diagnosis, GeneralChat, etc.)
                if kind == "on_chain_start" and name in known_chains:
                    active_chain = name
                elif kind == "on_chain_end" and name in known_chains:
                    active_chain = None

                # --- CASE 2: SUPPRESS INTERVIEW EXTRACTION ---
                if active_chain == "InterviewExtractionChain":
                    continue
                
                # --- CASE 3: TOOL UPDATES ---
                if "tool_search" in tags:
                    if kind == "on_tool_start":
                        yield f"data: {json.dumps({'type': 'tool', 'content': 'Searching...'})}\n\n"
                    elif kind == "on_tool_end":
                        yield f"data: {json.dumps({'type': 'tool', 'content': 'Search Completed'})}\n\n"
                    continue

                # --- CASE 4: DEFAULT TEXT STREAMING ---
                if kind in ["on_chat_model_stream", "on_llm_stream"]:
                    data = event["data"]
                    chunk = data.get("chunk")
                    content = chunk.content if chunk else ""
                    
                    if content:
                        # Handle special reasoning tokens (DeepSeek pattern)
                        if any(tag in content for tag in ["<think>", "<unused94>"]):
                            is_model_reasoning = True
                        
                        msg_type = "thinking" if is_model_reasoning else "text"
                        
                        if any(tag in content for tag in ["</think>", "<unused95>"]):
                            is_model_reasoning = False
                            msg_type = "thinking" # Closing tag still belongs to thinking

                        collected_content[msg_type].append(content)
                        yield f"data: {json.dumps({'type': msg_type, 'content': content})}\n\n"
                
                # Fallback for non-streaming models
                elif kind == "on_chat_model_end" and active_chain and active_chain != "ThinkingChain":
                     pass

            # Final Debug Summary
            debug_payload = {
                "thinking": "".join(collected_content["thinking"]),
                "plan": ", ".join(collected_content["plan"]),
                "text": "".join(collected_content["text"])
            }

            yield f"data: {json.dumps({'type': 'debug', 'content': json.dumps(debug_payload)})}\n\n"
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
