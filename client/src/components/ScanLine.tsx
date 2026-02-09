"use client";

interface ScanLineProps {
    isActive: boolean;
}

export function ScanLine({ isActive }: ScanLineProps) {
    if (!isActive) return null;

    return (
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
            <div
                className="w-full h-1 bg-white/70 shadow-[0_0_20px_rgba(255,255,255,0.8)] animate-scan"
            />
        </div>
    );
}
