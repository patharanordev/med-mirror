import os
import logging
from faster_whisper import WhisperModel
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class STTService:
    _instance = None
    model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(STTService, cls).__new__(cls)
            # Deferred loading to prevent import blocking
        return cls._instance

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def load_model(self):
        """
        Load the Whisper model with Cross-Platform support (No PyTorch dependency).
        Tries CUDA first, falls back to CPU.
        """
        if self.model:
            return

        model_size = settings.STT_MODEL_SIZE
        logger.info(f"STT: Using model size: {model_size}")
        
        # 1. Try Loading with CUDA (Windows/Linux GPU)
        try:
            logger.info(f"STT: Attempting to load '{model_size}' on CUDA (GPU)...")
            self.model = WhisperModel(model_size, device="cuda", compute_type="float16")
            logger.info("STT: Successfully loaded on CUDA (GPU). 🚀")
            return
        except Exception as e:
            logger.warning(f"STT: CUDA load failed ({e}). Falling back to CPU...")

        # 2. Fallback to CPU (macOS / No GPU)
        try:
            # use "int8" for CPU efficiency (especially on Mac M-series)
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8") 
            logger.info("STT: Successfully loaded on CPU (int8).")
        except Exception as e:
            logger.error(f"STT: CRITICAL - Failed to load model on CPU: {e}")
            raise e

    def transcribe(self, audio_file) -> str:
        """
        Transcribe audio file-like object.
        """
        if not self.model:
            logger.info("STT: Model not loaded. Loading now (Lazy Load)...")
            self.load_model()

        # Determine language to force
        # If model is English-only (ends with .en), we must use "en" or let it default.
        # Otherwise, use the configured AGENT_LANGUAGE (e.g., "th").
        lang_arg = settings.AGENT_LANGUAGE
        if settings.STT_MODEL_SIZE.endswith(".en"):
            lang_arg = "en"

        # beam_size=1 for greedy decoding (FASTEST)
        # Force language to prevent auto-detection errors on short audio
        segments, info = self.model.transcribe(audio_file, beam_size=1, language=lang_arg)
        
        # Collect text
        text = ""
        for segment in segments:
            text += segment.text
        
        return text.strip()

# Singleton instance
stt_service = STTService()
