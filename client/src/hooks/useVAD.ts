"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useMicVAD, utils } from "@ricky0123/vad-react";

/**
 * Robust VAD + Local Whisper Hook.
 * - Uses Silero VAD for reliable Speech Detection.
 * - Uses Manual AudioContext for Real-Time "Wave" Visualization.
 * - Uses Backend (FastAPI + Whisper) for STT (No Web Speech API).
 */
export function useVADInput(
    onSpeechEnd: (text: string) => void,
    isAgentSpeaking: boolean
) {
    // UI State
    const [transcript, setTranscript] = useState("");
    const [isProcessing, setIsProcessing] = useState(false);
    const [hadMisfire, setHadMisfire] = useState(false);

    // State mirror for UI
    const [isSpeechActive, setIsSpeechActive] = useState(false);

    // Audio Visualization Refs
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    // Expose raw data for UI visualizer
    const [audioDataForUi, setAudioDataForUi] = useState<Uint8Array | null>(null);

    // Logic Refs
    const isAgentSpeakingRef = useRef(isAgentSpeaking);
    const speechEndCallbackRef = useRef(onSpeechEnd);
    const isSpeechActiveRef = useRef(false);

    // Sync Props
    useEffect(() => {
        isAgentSpeakingRef.current = isAgentSpeaking;
    }, [isAgentSpeaking]);

    useEffect(() => {
        speechEndCallbackRef.current = onSpeechEnd;
    }, [onSpeechEnd]);

    // Initialize Audio & Stream manually to share between VAD and Visualizer
    useEffect(() => {
        let animationFrameId: number;

        const initAudio = async () => {
            if (typeof window === "undefined") return;

            try {
                if (mediaStreamRef.current) return;

                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaStreamRef.current = stream;

                // Create Context & Analyser
                const AudioContextClass = (window.AudioContext || (window as any).webkitAudioContext);
                const ctx = new AudioContextClass();
                audioContextRef.current = ctx;

                const analyser = ctx.createAnalyser();
                analyser.fftSize = 64;
                analyserRef.current = analyser;

                const source = ctx.createMediaStreamSource(stream);
                source.connect(analyser);

                // Animation Loop
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);

                const renderFrame = () => {
                    if (!analyserRef.current) return;
                    analyserRef.current.getByteFrequencyData(dataArray);
                    setAudioDataForUi(new Uint8Array(dataArray));
                    animationFrameId = requestAnimationFrame(renderFrame);
                };
                renderFrame();

            } catch (e) {
                console.error("Failed to initialize audio:", e);
            }
        };

        initAudio();

        return () => {
            if (animationFrameId) cancelAnimationFrame(animationFrameId);
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(track => track.stop());
                mediaStreamRef.current = null;
            }
            if (audioContextRef.current) {
                audioContextRef.current.close().catch(() => { });
                audioContextRef.current = null;
            }
        };
    }, []);

    // VAD Logic
    const vad = useMicVAD({
        startOnLoad: true,
        model: "v5",
        baseAssetPath: "/",
        onnxWASMBasePath: "/",
        // SHARE STREAM with Visualizer
        // @ts-ignore
        getStream: async () => {
            while (!mediaStreamRef.current) {
                await new Promise(r => setTimeout(r, 100));
            }
            return mediaStreamRef.current;
        },
        // @ts-ignore
        audioContext: audioContextRef.current || undefined,

        // Parameter Tuning
        positiveSpeechThreshold: 0.65,
        negativeSpeechThreshold: 0.4,
        preSpeechPadMs: 400,
        minSpeechMs: 100,
        redemptionMs: 1000,

        onSpeechStart: () => {
            console.log("VAD: Speech START");
            isSpeechActiveRef.current = true;
            setIsSpeechActive(true);
            setTranscript("Listening...");
        },

        onVADMisfire: () => {
            console.log("VAD: Misfire");
            isSpeechActiveRef.current = false;
            setIsSpeechActive(false);
            setTranscript("");
            // Show "again please" indicator
            setHadMisfire(true);
            setTimeout(() => setHadMisfire(false), 2000); // Auto-clear after 2 seconds
        },

        onSpeechEnd: async (audio) => {
            console.log("VAD: Speech END. Processing...");
            isSpeechActiveRef.current = false;
            setIsSpeechActive(false);

            if (!audio || audio.length === 0) {
                setTranscript("");
                return;
            }

            setIsProcessing(true);
            setTranscript("Transcribing...");

            try {
                // 1. Convert Float32Array to WAV Blob
                const wavBuffer = utils.encodeWAV(audio);
                const blob = new Blob([wavBuffer], { type: 'audio/wav' });
                const file = new File([blob], "speech.wav", { type: "audio/wav" });

                // 2. Upload to Local Whisper Backend
                const formData = new FormData();
                formData.append("file", file);

                const response = await fetch("/api/proxy/stt", {
                    method: "POST",
                    body: formData,
                });

                if (!response.ok) throw new Error("STT Server Error");

                const data = await response.json();
                const text = data.text?.trim();

                console.log("STT Result:", text);

                if (text && text.length > 0) {
                    setTranscript(text);
                    // Send to Callback
                    if (speechEndCallbackRef.current) {
                        speechEndCallbackRef.current(text);
                    }
                    // Clear after short delay
                    setTimeout(() => setTranscript(""), 2000);
                } else {
                    setTranscript("");
                }

            } catch (e) {
                console.error("STT Error:", e);
                setTranscript("Error");
            } finally {
                setIsProcessing(false);
            }
        }
    });

    const toggle = useCallback(() => {
        if (vad.listening) vad.pause();
        else vad.start();
    }, [vad]);

    return {
        isListening: vad.listening,
        toggle,
        userSpeaking: isSpeechActive,
        transcript,
        isSttActive: !vad.errored && !vad.loading, // Simplification
        audioData: audioDataForUi,
        hadMisfire, // Expose misfire state for UI indicator
    };
}
