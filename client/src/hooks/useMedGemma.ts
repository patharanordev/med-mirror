"use client";

import { useState, useCallback, useRef } from "react";

const API_AGENT = "http://localhost:8001";

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
    const lastContextRef = useRef("No specific detection yet.");
    const lastImageRef = useRef<string | null>(null);

    const sendMessage = useCallback(
        async (text: string) => {
            if (!text.trim()) return;

            const userMsg: Message = { role: "user", content: text };
            setMessages((prev) => [...prev, userMsg]);
            setIsTyping(true);

            const recentHistory = messages.slice(-10);
            const payload = {
                message: text,
                history: recentHistory,
                context: lastContextRef.current,
                image_url: lastImageRef.current,
            };

            try {
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
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value);
                        const lines = chunk.split("\n\n");

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
                                } catch {
                                    /* ignore parse errors */
                                }
                            }
                        }
                    }
                }
            } catch (e) {
                console.error(e);
                setMessages((prev) => [
                    ...prev,
                    { role: "assistant", content: "Error connecting to Agent." },
                ]);
            } finally {
                setIsTyping(false);
            }
        },
        [messages]
    );

    const updateContext = useCallback((skinVal: number, image?: string) => {
        setMetrics((prev) => ({ ...prev, skinArea: skinVal.toFixed(1) + "%" }));
        if (image) {
            lastImageRef.current = image;
        }
        if (skinVal > 10) {
            lastContextRef.current = `Detected significant skin area (${skinVal.toFixed(1)}% coverage). Analyze for potential lesions.`;
        }
    }, []);

    const updateInferenceTime = useCallback((time: number) => {
        setMetrics((prev) => ({ ...prev, inferenceTime: Math.round(time) + " ms" }));
    }, []);

    return { messages, sendMessage, isTyping, metrics, updateContext, updateInferenceTime };
}
