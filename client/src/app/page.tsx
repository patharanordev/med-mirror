"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { VideoFeed, VideoFeedRef } from "@/components/VideoFeed";
import { useMedGemma } from "@/hooks/useMedGemma";
import { useVADInput } from "@/hooks/useVAD";

export default function Home() {
  const videoRef = useRef<VideoFeedRef>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isAuto, setIsAuto] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, isTyping, metrics, updateContext, updateInferenceTime } =
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

  const { isListening, userSpeaking, transcript } = useVADInput(sendMessage, isTyping);

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
        <header>
          <div className="logo">
            MedMirror <span className="badge">EDGE</span>
          </div>
          <div className="status-indicator">
            <span className={`dot ${isStreaming ? 'connected' : ''}`} />
            {isStreaming ? 'RTX 4080 Active' : 'Camera Off'}
          </div>
        </header>

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

                  <div className="chat-input-area">
                    {userSpeaking && (
                      <div className="vad-indicator">
                        <span className="pulse" /> Listening...
                      </div>
                    )}
                    <input
                      type="text"
                      className={userSpeaking ? "typing-active" : ""}
                      value={transcript || input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder={isListening ? "Speak now or type..." : "Type a message..."}
                      autoComplete="off"
                    />
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
