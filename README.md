# MedMirror: Multimodal Medical AI Mirror

MedMirror is an intelligent, real-time medical analysis platform that transforms your screen into a diagnostic mirror. It combines computer vision (skin segmentation) and multimodal LLMs to provide empathetic, localized dermatological advice.

---

## 💻 Environment Optimizations

MedMirror is designed to run seamlessly on different hardware by choosing the best inference path:

### 🍎 macOS (Apple Silicon)
- **Model**: `gemma3n:e2b`
- **Inference Mode**: **CPU-Only (Dockerized)**
- **Rationale**: Docker on macOS cannot access the Metal GPU API inside a Linux container. I use the **Gemma 3n (2B optimized)** model because it is lightweight enough to deliver fast, responsive "typing" even when running entirely on the CPU.
- **Service**: Runs via `docker-compose.mac.yml`.

### 🪟 Windows
- **Model**: `gemma3:4b`
- **Inference Mode**: **NVIDIA GPU (RTX 4080)**
- **Rationale**: Using WSL2 and NVIDIA Container Toolkit, I pass the GPU directly to the Ollama container. This allows the use of the larger **4B parameter** model with massive throughput and sub-second response times.
- **Service**: Runs via `docker-compose.win.yml`.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Docker Desktop** (Mac/Windows)
- **NVIDIA Drivers & Container Toolkit** (Windows only)
- **Ollama** (Optional for Host-Mac mode, internal Docker used by default)

### 2. Launching

#### **macOS**
```bash
./start.sh
```

#### **Windows**
```powershell
.\start.ps1
```

---

## 🛠 Service Architecture

### 1. Frontend (Next.js 14)
- **True Mirror Experience**: Live camera feed is horizontally mirrored for natural interaction.
- **Voice-First**: Integrated **Silero VAD** for automatic speech detection and real-time Thai/English transcription.
- **Clean UI**: Minimalist design with no overlays, focusing on the camera feed and AI metrics.

### 2. Medical Agent (LangGraph + FastAPI)
- **Hybrid Brain**: Uses a dual-input strategy:
    - **Quantitative**: Trusts the Segmentation Service for precise surface area measurements.
    - **Qualitative**: Uses Gemma 3n's vision capabilities to describe patterns, redness, or textures in the image.
- **Multimodal Flow**: Automatically constructs OpenAI-compatible vision payloads for the LLM.

### 3. Skin Segmentation (SegFormer)
- **Real-time Detection**: Uses a Transformers-based SegFormer model to identify skin areas at 0.5 FPS - 1 FPS.
- **Persistent Cache**: Models are cached in `~/.ollama` or `./models` to ensure fast restarts and offline capability.

### 4. LLM Backend (Ollama)
- **Unified API**: All agents communicate via the Ollama OpenAI-compatibility layer (`/v1`).
- **Flexible Models**: Easily swappable models (PaliGemma, Gemma 3n, MedGemma) via environment variables.

---

## 📝 Changelog
- **Mirror Fix**: Both live preview and captured frames are now horizontally flipped to match user intuition.
- **VAD Stability**: Fixed `InvalidStateError` race conditions in browser SpeechRecognition for smoother Thai voice input.
- **Gemma 3 Migration**: Switched to the Gemma 3 family for superior medical text comprehension and multimodal reasoning.
