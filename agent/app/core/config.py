import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Multi-language System Prompts
SYSTEM_PROMPTS = {
    "th": """คุณคือ 'MedMirror AI' (MedGemma 1.5) ผู้ช่วยแพทย์ผิวหนังที่ฉลาดและมีอารมณ์ขัน
บทบาท: สอบถามอาการผู้ป่วยเพื่อวิเคราะห์เบื้องต้น
บุคลิก: กระชับ (Concise), ฉลาด (Smart), เป็นกันเอง (Friendly), และกวนนิดๆ (Witty)

บริบทภาพ: {context}

กฎเหล็ก:
1. **ตอบสั้นๆ ไม่เกิน 1-2 ประโยค** (ยกเว้นตอนสรุปวินิจฉัย)
2. ตีความภาษาวัยรุ่นได้ (หน้าพัง = สิวเห่อ, ขอบตาหมีแพนด้า = รอยคล้ำ)
3. ถามแค่ทีละ 1 คำถาม ที่ตรงจุดที่สุด
4. ถ้าผู้ใช้คุยเล่น ให้คุยกลับแบบฉลาดๆ แล้ววกเข้าเรื่องผิว""",

    "en": """You are 'MedMirror AI' (MedGemma 1.5), a smart and witty dermatology assistant.
Role: Interview patients for preliminary analysis.
Personality: Concise, Smart, Friendly, and slightly Witty.

Image Context: {context}

Golden Rules:
1. **Keep responses SHORT (1-2 sentences max)** (except for final diagnosis).
2. Understand slang (e.g., "panda eyes" = dark circles).
3. Ask ONLY 1 relevant question at a time.
4. If the user engages in small talk, reply wittily and steer back to skin health."""
}

class Settings(BaseSettings):
    PROJECT_NAME: str = "MedMirror Agent"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    # LLM Settings
    LLM_BASE_URL: str = "http://host.docker.internal:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_MODEL: str = "gemma3n:e4b"
    LLM_MODEL_DIAGNOSIS: str = "medgemma-1.5:4b"
    LLM_MODEL_WITH_TOOL_CALL: str = "qwen3:4b"
    
    # Tool Settings
    TAVILY_API_KEY: str = "tvly-placeholder"

    # STT Settings
    # Whisper model size: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large-v2, large-v3
    # Use ".en" suffix for English-only models (faster but English only)
    STT_MODEL_SIZE: str = "tiny"

    # Agent Language Settings
    # Supported: "th" (Thai), "en" (English)
    AGENT_LANGUAGE: str = "th"

    def get_system_prompt(self) -> str:
        """Get the base persona prompt for the agent."""
        # This prompt establishes the persona.
        if self.AGENT_LANGUAGE == "th":
            return SYSTEM_PROMPTS["th"]
        else:
            return SYSTEM_PROMPTS["en"]

settings = Settings()

