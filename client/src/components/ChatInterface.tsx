"use client";

import { useEffect, useRef, memo } from "react";
import { Send, Mic } from "lucide-react";
import type { Message } from "@/hooks/useMedGemma";

import { useSystemStatus } from "@/hooks/useSystemStatus";

interface ChatInterfaceProps {
    messages: Message[];
    onSend: () => void;
    input: string;
    setInput: (value: string) => void;
    listening: boolean;
    userSpeaking: boolean;
}

// Memoized message bubble for performance
const MessageBubble = memo(function MessageBubble({
    msg,
    index
}: {
    msg: Message;
    index: number;
}) {
    return (
        <div
            className={`flex animate-fadeIn ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            style={{ animationDelay: `${index * 50}ms` }}
        >
            <div
                className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed glass text-shadow-sm ${msg.role === "user"
                    ? "text-white/90 rounded-br-none border-r-4 border-white/30"
                    : "text-blue-100 rounded-bl-none border-l-4 border-white"
                    }`}
            >
                {msg.content || (
                    <span className="animate-pulse text-white/50">Thinking...</span>
                )}
            </div>
        </div>
    );
});

export const ChatInterface = memo(function ChatInterface({
    messages,
    onSend,
    input,
    setInput,
    listening,
    userSpeaking,
}: ChatInterfaceProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const systemStatus = useSystemStatus();

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="fixed top-0 right-0 h-full w-[420px] glass border-l border-white/10 flex flex-col z-40 shadow-2xl">
            {/* Header */}
            <div className="p-6 border-b border-white/10 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center font-bold text-lg shadow-lg shadow-purple-500/30">
                    AI
                </div>
                <div>
                    <h2 className="font-bold text-lg text-shadow">MedMirror Assistant</h2>
                    <div className="flex items-center gap-2 text-xs text-white/50">
                        <span className={`w-2 h-2 rounded-full ${systemStatus.llm === "ready" ? "bg-green-500 animate-pulse-green" : "bg-yellow-500 animate-pulse"}`} />
                        Online • {systemStatus.modelName || "Connecting..."}
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide">
                {messages.map((msg, i) => (
                    <MessageBubble key={i} msg={msg} index={i} />
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input Area */}
            <div className="p-6 border-t border-white/10 glass">
                {userSpeaking && (
                    <div className="text-center text-xs text-purple-400 mb-3 animate-pulse font-bold tracking-widest uppercase">
                        🎤 Listening...
                    </div>
                )}

                <div className="relative flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && onSend()}
                        placeholder={listening ? "Speak now..." : "Type a message..."}
                        className="flex-1 bg-white/5 border border-white/10 rounded-xl pl-4 pr-4 py-3 focus:outline-none focus:border-white/30 transition-all placeholder:text-white/20 text-shadow-sm"
                    />

                    {/* Mic indicator when listening */}
                    {listening && (
                        <div className="w-10 h-10 flex items-center justify-center rounded-full bg-red-500/20 border border-red-500/50 animate-pulse-red">
                            <Mic size={18} className="text-red-400" />
                        </div>
                    )}

                    <button
                        onClick={onSend}
                        className="w-10 h-10 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 border border-white/20 transition-all btn-glow"
                    >
                        <Send size={18} className="text-white/80" />
                    </button>
                </div>
            </div>
        </div>
    );
});
