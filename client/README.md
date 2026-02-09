# MedMirror Client

The frontend application for MedMirror, built with **Next.js 14**, providing a real-time, AI-driven medical analysis interface.

## Core Features

### 1. Real-time Video Analysis
- **Live Stream**: High-definition camera integration with user-facing mode optimization.
- **Dynamic Segmentation**: Real-time skin detection using a dedicated segmentation backend.
- **Auto-Segmentation Mode**: Automatic periodic frame capture and analysis (0.5 FPS) for continuous monitoring.
- **Manual Capture**: On-demand "Analyze" button to capture the current frame for immediate AI evaluation.

### 2. Voice Activity Detection (VAD) & Interaction
- **Automatic Activation**: VAD starts automatically on page load (Start-on-Load).
- **Intelligent Listening**: Real-time detection of speech start and end using Silero VAD v5.
- **Visual Feedback**: Pulse-animated "Listening..." indicator that responds to voice activity.
- **Interim Transcription**: Real-time, localized (Thai/English) transcription appearing in the chat box as the user speaks.
- **Hands-free Messaging**: Messages are automatically sent to the agent when the user stops speaking.

### 3. Multimodal AI Integration
- **Context-Aware Chat**: Interactive chat interface powered by an LLM agent.
- **Vision-Language Analysis**: Sends the latest captured frame (base64) alongside text messages for visual diagnostic support.
- **Streaming Responses**: Token-by-token streaming from the agent for a responsive, "typing" experience.
- **Metric Dashboard**: Real-time tracking of skin area percentage and inference latency.

### 4. Robust Performance & Architecture
- **Web Audio Worklets**: High-performance audio processing for VAD to prevent main-thread blocking.
- **Clean State Management**: Uses React hooks (`useVAD`, `useMedGemma`) and refs to prevent stale closures and ensure UI synchronization.
- **Dockerized Deployment**: Fully containerized for easy setup on macOS (Apple Silicon/Podman) and Linux.

## Technical Details
- **Framework**: Next.js 14 (App Router)
- **State**: React Hooks + Refs
- **VAD Library**: `@ricky0123/vad-react`
- **Models**: Silero VAD (ONNX), ONNX Runtime Web
- **Icons**: Lucide React
