from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router as api_router

from contextlib import asynccontextmanager
import asyncio
from app.services.stt_service import stt_service
from app.services.agent_graph import agent_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load STT & LLM in background (Non-blocking)
    print("LIFESPAN: Triggering Background Warmup...")
    asyncio.create_task(asyncio.to_thread(stt_service.load_model))
    asyncio.create_task(agent_service.warmup())
    yield
    # Shutdown logic (if any)

def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
    
    # Set all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router)
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
