"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { VideoFeed, VideoFeedRef } from "@/components/VideoFeed";
import { useMedGemma } from "@/hooks/useMedGemma";
import { useVADInput } from "@/hooks/useVAD";
import { Mic, Ear, Activity, Brain, Loader2, Video, Eye } from "lucide-react";
import { AudioWave } from "@/components/AudioWave";
import { useSystemStatus } from "@/hooks/useSystemStatus";

export default function Home() {
  const videoRef = useRef<VideoFeedRef>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isAuto, setIsAuto] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // System Status Hook (Warmup Indicators)
  const systemStatus = useSystemStatus();

  const { messages, sendMessage, isTyping, metrics, updateContext, updateInferenceTime, hasImage } =
    useMedGemma();

  const [input, setInput] = useState("");

  // Scroll chat to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleCameraToggle = useCallback(async () => {
    if (isStreaming) {
      videoRef.current?.stopCamera();
      setIsStreaming(false);
      setIsAuto(false);
    } else {
      await videoRef.current?.startCamera();
      setIsStreaming(true);
    }
  }, [isStreaming]);

  const handleAutoToggle = useCallback(() => {
    setIsAuto(prev => !prev);
  }, []);

  const handleManualCapture = useCallback(() => {
    if (!isStreaming) return;
    videoRef.current?.manualCapture();
  }, [isStreaming]);

  const handleInference = useCallback((time: number, skinVal: number, image?: string) => {
    updateInferenceTime(time);
    updateContext(skinVal, image);
  }, [updateInferenceTime, updateContext]);

  const handleSendMessage = useCallback(() => {
    if (input.trim()) {
      sendMessage(input);
      setInput("");
    }
  }, [input, sendMessage]);

  const { isListening, userSpeaking, transcript, isSttActive, audioData, hadMisfire } = useVADInput(sendMessage, isTyping);

  return (
    <div className="w-screen h-screen bg-black text-white overflow-hidden relative">
      {/* LAYER 1: VIDEO BACKGROUND */}
      <div className="video-background">
        <VideoFeed
          ref={videoRef}
          onInference={handleInference}
          isAutoMode={isAuto}
        />
        {/* Scan line overlay */}
        <div className={`overlay-scan-fx ${isAuto ? 'scanning' : ''}`}>
          <div className="scan-line" />
        </div>
      </div>

      {/* LAYER 2: UI OVERLAY */}
      <div className="app-overlay">
        {/* Header */}
        <header className="flex justify-between items-center p-4 bg-gradient-to-b from-black/80 to-transparent z-50 fixed top-0 w-full">
          <div className="logo font-bold text-xl tracking-wider">
            MedMirror <span className="text-xs bg-cyan-500 text-black px-1 rounded ml-1">EDGE</span>
          </div>

          {/* SYSTEM STATUS TRAY */}
          <div className="status-tray flex gap-4 items-center bg-black/40 backdrop-blur-md px-4 py-2 rounded-full border border-white/10">
            {/* 1. Camera Status */}
            <div className={`icon-box transition-colors duration-300 ${isStreaming ? 'text-green-400' : 'text-gray-500'}`} title={isStreaming ? "RTX 4080 Active" : "Camera Off"}>
              <Video size={20} />
            </div>

            <div className="w-px h-4 bg-white/20"></div>

            {/* 2. Mic / VAD Status */}
            <div className={`icon-box transition-colors duration-300 ${isListening ? 'text-green-400' : 'text-gray-600'}`} title="VAD Listening">
              <Mic size={20} />
            </div>

            {/* 3. STT Engine Status */}
            <div
              className={`icon-box transition-colors duration-300 ${systemStatus.stt === 'loading' ? 'text-yellow-400 animate-pulse' :
                systemStatus.stt === 'ready' ? 'text-cyan-400' : 'text-gray-700'
                }`}
              title={
                systemStatus.stt === 'loading' ? "STT Warming Up..." :
                  systemStatus.stt === 'ready' ? "STT Engine Ready" : "STT Offline"
              }
            >
              <Ear size={20} />
            </div>

            {/* 4. Transcription Activity */}
            <div className={`icon-box transition-all duration-200 ${userSpeaking ? 'text-yellow-400 animate-pulse scale-110' : 'text-gray-700'}`} title="Transcribing Speech">
              <Activity size={20} />
            </div>

            <div className="w-px h-4 bg-white/20"></div>

            {/* 5. Agent Processing */}
            <div
              className={`icon-box transition-colors duration-300 ${isTyping ? 'text-purple-400' :
                systemStatus.llm === 'loading' ? 'text-yellow-400 animate-pulse' :
                  systemStatus.llm === 'ready' ? 'text-blue-400' : 'text-gray-700'
                }`}
              title={
                isTyping ? "AI Generating..." :
                  systemStatus.llm === 'loading' ? "LLM Warming Up..." :
                    systemStatus.llm === 'ready' ? "AI Agent Ready" : "AI Offline"
              }
            >
              {isTyping ? <Loader2 size={20} className="animate-spin" /> : <Brain size={20} />}
            </div>
          </div>
        </header>

        {/* CENTER BOTTOM AUDIO WAVE */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2 pointer-events-none">
          <AudioWave isActive={userSpeaking} audioData={audioData} />
          {/* Status Labels */}
          <span className={`text-xs font-mono uppercase tracking-widest transition-opacity duration-300 ${userSpeaking ? 'opacity-100 text-green-400' : 'opacity-0'}`}>
            Listening
          </span>
          {/* Misfire Indicator - "Again please?" */}
          <span className={`text-xs font-mono tracking-wider transition-all duration-300 ${hadMisfire ? 'opacity-100 text-red-400 animate-pulse' : 'opacity-0'}`}>
            🔄 Again please?
          </span>
        </div>

        {/* Main Content */}
        <main>
          <div className="cols">
            {/* Left Column: Metrics & Controls */}
            <div className="col-left">
              <div className="metrics-card">
                <h3>Vision Metrics</h3>
                <div className="metric-row">
                  <div className="metric">
                    <span className="label">Inference Time</span>
                    <span className="value">{metrics.inferenceTime}</span>
                  </div>
                  <div className="metric">
                    <span className="label">Skin Area</span>
                    <span className="value">{metrics.skinArea}</span>
                  </div>
                </div>
              </div>

              <div className="controls">
                <button
                  onClick={handleCameraToggle}
                  className={isStreaming ? 'action-btn' : 'primary-btn'}
                >
                  {isStreaming ? 'Stop Camera' : 'Start Camera'}
                </button>
                <button
                  onClick={handleManualCapture}
                  className="action-btn"
                  disabled={!isStreaming}
                >
                  Analyze Skin
                </button>
                <div className="toggle-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={isAuto}
                      onChange={handleAutoToggle}
                      disabled={!isStreaming}
                    />
                    {' '}Auto-Segment Stream
                  </label>
                </div>
              </div>
            </div>

            {/* Spacer */}
            <div className="col-spacer" />

            {/* Right Column: Chat */}
            <div className="col-right">
              <div className="agent-section">
                <div className="chat-container">
                  <div className="chat-header">
                    <div className="avatar">AI</div>
                    <div className="agent-info">
                      <h4>MedMirror Assistant</h4>
                      <span className="status">Online • Gemma-2b</span>
                    </div>
                  </div>

                  <div className="chat-messages">
                    {messages.map((msg, i) => (
                      <div key={i} className={`message ${msg.role}`}>
                        <div className="bubble">
                          {msg.content || <span className="typing">typing...</span>}
                        </div>
                      </div>
                    ))}
                    <div ref={bottomRef} />
                  </div>

                  <div className="chat-input-area relative">
                    {/* Live Transcript Bubble */}
                    {(userSpeaking || transcript) && (
                      <div className="absolute bottom-full left-0 mb-2 w-full px-4 py-2">
                        <div className="bg-black/60 backdrop-blur-md border border-yellow-500/50 text-yellow-100 rounded-lg p-3 shadow-lg flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
                          <span className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-yellow-500"></span>
                          </span>
                          <span className="font-mono text-sm">
                            {transcript || "Listening..."}
                          </span>
                        </div>
                      </div>
                    )}

                    <input
                      type="text"
                      className={userSpeaking ? "typing-active pl-4" : "pl-4"}
                      value={input} // Use manual input only here. Transcript is shown above.
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder={isListening ? "Type or Speak..." : "Type a message..."}
                      autoComplete="off"
                    />
                    {/* Multimodal Indicator */}
                    {hasImage && (
                      <div className="absolute right-12 top-1/2 -translate-y-1/2 text-cyan-400 animate-pulse" title="Analysis Image Attached">
                        <Eye size={20} />
                      </div>
                    )}
                    <button type="button" onClick={handleSendMessage}>➤</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
