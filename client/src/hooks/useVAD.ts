"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useMicVAD } from "@ricky0123/vad-react";

export function useVADInput(
    onSpeechEnd: (text: string) => void,
    isAgentSpeaking: boolean
) {
    const [transcript, setTranscript] = useState("");
    const recognitionRef = useRef<any>(null);
    const transcriptBuffer = useRef("");
    const isAgentSpeakingRef = useRef(isAgentSpeaking);
    const isRecognitionStartingRef = useRef(false);

    // Sync ref with prop to avoid stale closures in VAD callbacks
    useEffect(() => {
        isAgentSpeakingRef.current = isAgentSpeaking;
    }, [isAgentSpeaking]);

    useEffect(() => {
        if (typeof window !== "undefined") {
            const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            if (SpeechRecognitionAPI) {
                const rec = new SpeechRecognitionAPI();
                rec.continuous = true;
                rec.interimResults = true;
                rec.lang = "th-TH"; // Restore Thai support as requested

                rec.onresult = (event: any) => {
                    let interim = "";
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            transcriptBuffer.current += event.results[i][0].transcript + " ";
                        } else {
                            interim += event.results[i][0].transcript;
                        }
                    }
                    const fullTranscript = (transcriptBuffer.current + interim).trim();
                    setTranscript(fullTranscript); // Immediate state update for UI
                };

                rec.onerror = (e: any) => {
                    if (e.error !== "no-speech") {
                        console.error("STT Error", e);
                    }
                    // Reset starting flag if an error occurs during recognition
                    isRecognitionStartingRef.current = false;
                };

                rec.onend = () => {
                    console.log("STT: Recognition ended.");
                    // Reset starting flag when recognition ends
                    isRecognitionStartingRef.current = false;
                };

                recognitionRef.current = rec;
            }
        }
    }, []);

    const safeStartRecognition = useCallback(() => {
        if (recognitionRef.current && !isRecognitionStartingRef.current) {
            try {
                isRecognitionStartingRef.current = true; // Set flag before attempting to start
                setTranscript("");
                transcriptBuffer.current = "";
                recognitionRef.current.start();
                console.log("STT: Recognition started.");
            } catch (e: any) {
                // Handle InvalidStateError specifically, which means it's already running
                if (e.name === "InvalidStateError") {
                    console.log("STT: Recognition already running or in an invalid state to start.");
                } else {
                    console.error("STT: Failed to start recognition:", e);
                }
                isRecognitionStartingRef.current = false; // Reset flag if start failed
            }
        } else if (isRecognitionStartingRef.current) {
            console.log("STT: Recognition start already in progress or already running.");
        }
    }, []);

    const vad = useMicVAD({
        startOnLoad: true,
        model: "v5",
        baseAssetPath: "/",
        onnxWASMBasePath: "/",
        onSpeechStart: () => {
            console.log("VAD: Speech Start");
            if (!isAgentSpeakingRef.current) {
                safeStartRecognition();
            }
        },
        onSpeechEnd: () => {
            console.log("VAD: Speech End");
            // Small delay to capture final transcription pieces
            setTimeout(() => {
                if (recognitionRef.current) {
                    try {
                        recognitionRef.current.stop();
                        console.log("STT: Recognition stopped.");
                    } catch (e: any) {
                        // Handle InvalidStateError specifically, which means it's already stopped
                        if (e.name === "InvalidStateError") {
                            console.log("STT: Recognition already stopped or in an invalid state to stop.");
                        } else {
                            console.error("STT: Failed to stop recognition:", e);
                        }
                    }
                }

                const final = transcriptBuffer.current.trim() || transcript.trim();
                console.log("VAD: Final Transcript captured:", final);

                if (final.length > 0) {
                    onSpeechEnd(final);
                    setTranscript("");
                    transcriptBuffer.current = "";
                }
            }, 800);
        },
    });

    const toggle = useCallback(() => {
        if (vad.listening) {
            vad.pause();
        } else {
            vad.start();
        }
    }, [vad]);

    return {
        isListening: vad.listening,
        toggle,
        userSpeaking: vad.userSpeaking,
        transcript,
    };
}
