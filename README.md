# MedMirror: Multimodal Medical AI Mirror

MedMirror is an intelligent, real-time medical analysis platform that transforms your screen into a diagnostic mirror. It combines computer vision (skin segmentation), local speech recognition, and multimodal LLMs to provide empathetic, localized dermatological advice.

---

## 🌟 Key Features

### 🩺 **Real-Time Skin Analysis**
- **Automatic Detection**: Instantly identifies various skin conditions (redness, lesions, acne) using the integrated SegFormer model.
- **Live Visualization**: See precise segmentation overlays on your video feed in real-time (0.5 - 1 FPS).

### 🗣️ **Talk to the Mirror (STT)**
- **Speech-to-Text**: Integrated transcription allowing you to talk directly to the mirror.
- **Hands-Free**: Talk naturally without pressing buttons. The system auto-detects speech and transcribes it instantly so you can focus on yourself.

### 🧠 **Empathetic Medical Interview**
- **Context-Aware AI**: The agent "sees" the skin analysis and asks relevant follow-up questions (symptom duration, pain levels, history).
- **Thai Language Support**: Fluent in Thai for approachable and localized medical advice.

### �️ **Visual Context Assurance**
- **Multimodal Awareness**: The "Eye" icon 👁️ signals when the AI has captured a clear image of your skin condition.
- **Zero-Wait Response**: The system initializes in the background, allowing you to start chatting the moment the page loads.

---

## 💻 Environment & Models

MedMirror is designed to run seamlessly on different hardware by choosing the best inference path:

### 🍎 macOS (Apple Silicon)
- **Model**: `gemma3n:e2b` (Ollama)
- **STT**: `faster-whisper` (CPU)
- **Inference Mode**: **CPU-Optimized (Dockerized)**
- **Service**: Runs via `docker-compose.mac.yml`.

### 🪟 Windows (NVIDIA GPU)
- **Model**: `gemma3:4b` (Ollama)
- **STT**: `faster-whisper` (CUDA/GPU)
- **Inference Mode**: **NVIDIA RTX 4080 Acceleration**
- **Service**: Runs via `docker-compose.win.yml` with CUDA 12.2 runtime.

### 🔧 Configuration via .env
You can customize the agent language and STT model size in `.env.local` (or your OS-specific env file):

```env
# Agent Language (th = Thai, en = English)
AGENT_LANGUAGE=th

# Whisper STT Model Size 
# Options: tiny, tiny.en, base, small, medium, large-v3
STT_MODEL_SIZE=tiny
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Docker Desktop**
- **NVIDIA Drivers & Container Toolkit** (Windows only)
- **Ollama** (Optional for Host-Mac mode)

### 2. Pull Gemma Model
#### **macOS**
```bash
ollama pull gemma3n:e2b
```

#### **Windows**
```powershell
ollama pull gemma3:4b
```

### 3. Launching
#### **macOS**
```bash
docker-compose -f docker-compose.mac.yml up --build
```

#### **Windows**
```powershell
docker-compose -f docker-compose.win.yml up --build
```
*(Or use provided `start.bat` / `start.sh` scripts)*

---

## 🛠 Enhanced Architecture

### 1. Frontend (Next.js 15)
- **Smart Proxy (`/api/proxy`)**: New internal proxy routing handles all CORS and container networking seamlessly.
- **System Status Hook**: Real-time polling of backend health endpoints (`/health`).
- **Stream Buffer**: Robust parsing logic handles fragmented SSE packets from the LLM.

### 2. Medical Agent (FastAPI + LangGraph)
- **Stateful Graph**: Manages conversation history, context, and image inputs.
- **Hybrid Streaming**: Supports both token-by-token streaming and bulk fallback.
- **Multimodal Handler**: Automatically formats text + image instructions for the Vision LLM.

### 3. Local STT Service (`faster-whisper`)
- **Privacy First**: All audio processed locally within the container.
- **Latency Optimized**: Using `tiny.en` model + beam size 1 for sub-200ms transcription.

### 4. Skin Segmentation (SegFormer)
- **Real-time Detection**: Uses a Transformers-based SegFormer model to identify skin areas at 0.5 FPS - 1 FPS.
- **Persistent Cache**: Models are cached to ensure fast restarts and offline capability.

### 5. LLM Backend (Ollama)
- **Unified API**: All agents communicate via the Ollama OpenAI-compatibility layer (`/v1`).
- **Flexible Models**: Easily swappable models (Gemma 3, MedGemma) via environment variables.

---

## 🧪 Verification
Run the automated streaming test to verify backend health:
```bash
python agent/tests/test_streaming.py
```

---

## � Issues Resolved

### Recent Fixes
- **Resilience**: Fixed "infinite typing" by implementing callback config propagation in LangGraph.
- **Fix**: Resolved `404 Not Found` proxy errors by aliasing `/health`.
- **UI**: Added animated status tray (Mic, Ear, Brain, Eye).
- **Docker**: Split builds for optimized Windows (CUDA) vs Mac (CPU) images.

### Previous Improvements
- **Mirror Fix**: Both live preview and captured frames are now horizontally flipped to match user intuition.
- **VAD Stability**: Fixed `InvalidStateError` race conditions in browser SpeechRecognition for smoother Thai voice input.
- **Gemma 3 Migration**: Switched to the Gemma 3 family for superior medical text comprehension and multimodal reasoning.
