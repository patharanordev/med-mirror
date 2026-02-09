"use client";

import { useState, useCallback, useRef, useEffect } from "react";

const API_AGENT = "/api/proxy";

export type Message = {
    role: "user" | "assistant";
    content: string;
};

export function useMedGemma() {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "assistant",
            content:
                "สวัสดีครับ ผมคือ AI ผู้ช่วยทางการแพทย์ \nเริ่มต้นโดยการตรวจจับผิวหนังของคุณ แล้วเรามาคุยกันครับ",
        },
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const [metrics, setMetrics] = useState({
        inferenceTime: "0 ms",
        skinArea: "0%",
    });
    const [hasImage, setHasImage] = useState(false);
    const lastContextRef = useRef("No specific detection yet.");
    const lastImageRef = useRef<string | null>(null);

    // Keep a ref of messages for access inside sendMessage without dependencies
    const messagesRef = useRef<Message[]>(messages);
    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);

    const sendMessage = useCallback(
        async (text: string) => {
            console.log("sendMessage called with:", text);
            if (!text.trim()) return;

            const userMsg: Message = { role: "user", content: text };
            setMessages((prev) => [...prev, userMsg]);
            setIsTyping(true);

            // Use ref to get history without creating a dependency
            const recentHistory = messagesRef.current.slice(-10);

            const payload = {
                message: text,
                history: recentHistory,
                context: lastContextRef.current,
                image_url: lastImageRef.current,
            };

            // Clear image after sending (or keep it? Usually keep for context until new scan)
            // Strategy: Keep it until updated. 

            try {
                console.log("Sending payload to agent...");
                const response = await fetch(`${API_AGENT}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) throw new Error("Agent API Error");

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();

                let assistantText = "";
                setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

                if (reader) {
                    let buffer = "";
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value, { stream: true });
                        // console.log("DEBUG: Received chunk:", chunk); // Uncomment to debug
                        buffer += chunk;

                        const lines = buffer.split("\n\n");
                        // Keep the last part back in buffer (it might be incomplete)
                        buffer = lines.pop() || "";

                        for (const line of lines) {
                            if (line.startsWith("data: ")) {
                                const dataStr = line.replace("data: ", "").trim();
                                if (dataStr === "[DONE]") break;
                                try {
                                    const data = JSON.parse(dataStr);
                                    if (data.content) {
                                        assistantText += data.content;
                                        setMessages((prev) => {
                                            const newMsgs = [...prev];
                                            newMsgs[newMsgs.length - 1].content = assistantText;
                                            return newMsgs;
                                        });
                                    }
                                } catch (e) {
                                    console.error("Parse Error:", e, "Line:", line);
                                }
                            }
                        }
                    }
                }
                console.log("Message cycle complete, Full Text:", assistantText);
            } catch (e) {
                console.error("sendMessage Error:", e);
                setMessages((prev) => [
                    ...prev,
                    { role: "assistant", content: "Error connecting to Agent." },
                ]);
            } finally {
                setIsTyping(false);
            }
        },
        [] // No dependencies! Stable function identity.
    );

    const updateContext = useCallback((skinVal: number, image?: string) => {
        setMetrics((prev) => ({ ...prev, skinArea: skinVal.toFixed(1) + "%" }));
        if (image) {
            lastImageRef.current = image;
            setHasImage(true);
        }
        if (skinVal > 10) {
            lastContextRef.current = `Detected significant skin area (${skinVal.toFixed(1)}% coverage). Analyze for potential lesions.`;
        }
    }, []);

    const updateInferenceTime = useCallback((time: number) => {
        setMetrics((prev) => ({ ...prev, inferenceTime: Math.round(time) + " ms" }));
    }, []);

    return { messages, sendMessage, isTyping, metrics, updateContext, updateInferenceTime, hasImage };
}
