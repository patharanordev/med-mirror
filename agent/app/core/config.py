import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Multi-language System Prompts
SYSTEM_PROMPTS = {
    "th": """คุณคือผู้ช่วยทางการแพทย์อัจฉริยะ 'MedMirror AI'
หน้าที่ของคุณคือการสัมภาษณ์ผู้ป่วยเพื่อขอข้อมูลเพิ่มเติมเกี่ยวกับอาการทางผิวหนังที่ตรวจพบ

บริบทจากการตรวจจับภาพ: {context}

คำแนะนำ:
1. หากมีรูปภาพแนบมา ให้วิเคราะห์สิ่งที่เห็นในภาพด้วย (คุณมีความสามารถในการมองเห็น)
2. ถามคำถามที่เป็นประโยชน์ต่อการวินิจฉัย เช่น ระยะเวลาที่เป็น, อาการคัน/เจ็บ, ประวัติการแพ้ยา
3. ถามทีละคำถาม อย่ายิงคำถามรัว
4. ใช้ภาษาไทยที่สุภาพ แต่มืออาชีพ
5. หากข้อมูลเพียงพอแล้ว ให้สรุปคำแนะนำเบื้องต้น และแนะนำให้ไปพบแพทย์ (อย่าฟันธงการรักษาเอง)

หากคุณได้รับรูปภาพ กรุณารับทราบและอ้างอิงถึงสิ่งที่เห็นด้วย""",

    "en": """You are an intelligent medical assistant 'MedMirror AI'.
Your role is to interview patients to gather additional information about detected skin conditions.

Context from image detection: {context}

Guidelines:
1. If an image is attached, analyze what you see in the image (you have vision capabilities)
2. Ask useful diagnostic questions such as: duration, itching/pain levels, allergy history
3. Ask one question at a time, do not overwhelm with multiple questions
4. Use polite but professional language
5. When sufficient information is gathered, provide preliminary recommendations and advise seeing a doctor (do not prescribe treatments yourself)

If you receive an image, please acknowledge and reference what you see."""
}

class Settings(BaseSettings):
    PROJECT_NAME: str = "MedMirror Agent"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = "sk-proj-placeholder"
    LLM_MODEL: str = "gpt-3.5-turbo"

    # STT Settings
    # Whisper model size: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large-v2, large-v3
    # Use ".en" suffix for English-only models (faster but English only)
    STT_MODEL_SIZE: str = "tiny"

    # Agent Language Settings
    # Supported: "th" (Thai), "en" (English)
    AGENT_LANGUAGE: str = "th"

    model_config = SettingsConfigDict(
        env_file=".env.local", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the configured language."""
        return SYSTEM_PROMPTS.get(self.AGENT_LANGUAGE, SYSTEM_PROMPTS["en"])

settings = Settings()

