"use client";

import { Camera, CameraOff, BrainCircuit, Activity, Scan } from "lucide-react";
import { memo } from "react";

interface ControlsProps {
    isStreaming: boolean;
    onToggleCamera: () => void;
    isAuto: boolean;
    onToggleAuto: () => void;
    isVAD: boolean;
    onToggleVAD: () => void;
    onManualCapture: () => void;
}

export const Controls = memo(function Controls({
    isStreaming,
    onToggleCamera,
    isAuto,
    onToggleAuto,
    isVAD,
    onToggleVAD,
    onManualCapture,
}: ControlsProps) {
    return (
        <div className="fixed bottom-8 left-8 flex flex-col gap-4 z-50">
            {/* Primary Camera Button */}
            <button
                onClick={onToggleCamera}
                className={`flex items-center gap-2 px-6 py-3 rounded-full backdrop-blur-md border transition-all btn-glow text-shadow-sm ${isStreaming
                        ? "bg-red-500/20 border-red-500/50 text-red-200"
                        : "bg-white/10 border-white/20 hover:bg-white/20 text-white"
                    }`}
            >
                {isStreaming ? <CameraOff size={20} /> : <Camera size={20} />}
                {isStreaming ? "Stop Camera" : "Start Camera"}
            </button>

            {/* Secondary Controls Row */}
            <div className="flex gap-2">
                {/* Manual Capture */}
                <button
                    onClick={onManualCapture}
                    disabled={!isStreaming}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl backdrop-blur-md border transition-all btn-glow ${isStreaming
                            ? "bg-white/10 border-white/20 text-white hover:bg-white/20"
                            : "bg-black/20 border-white/5 text-gray-600 cursor-not-allowed"
                        }`}
                >
                    <Scan size={18} />
                    Analyze
                </button>

                {/* Auto Segment Toggle */}
                <button
                    onClick={onToggleAuto}
                    disabled={!isStreaming}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl backdrop-blur-md border transition-all ${isAuto
                            ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-200"
                            : isStreaming
                                ? "bg-black/40 border-white/10 text-gray-400 hover:bg-black/60"
                                : "bg-black/20 border-white/5 text-gray-600 cursor-not-allowed"
                        }`}
                >
                    <Activity size={18} />
                    Auto
                </button>

                {/* VAD Toggle */}
                <button
                    onClick={onToggleVAD}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl backdrop-blur-md border transition-all ${isVAD
                            ? "bg-purple-500/20 border-purple-500/50 text-purple-200 animate-pulse-red"
                            : "bg-black/40 border-white/10 text-gray-400 hover:bg-black/60"
                        }`}
                >
                    <BrainCircuit size={18} />
                    VAD
                </button>
            </div>
        </div>
    );
});
