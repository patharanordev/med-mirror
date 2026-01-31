"use client";

import { memo, useMemo } from "react";

interface VoiceWaveAnimationProps {
    isActive: boolean;
    isSpeaking: boolean;
    volume: number; // 0-1 normalized volume
}

export const VoiceWaveAnimation = memo(function VoiceWaveAnimation({
    isActive,
    isSpeaking,
    volume,
}: VoiceWaveAnimationProps) {
    // Calculate bar heights based on volume with variation
    const barHeights = useMemo(() => {
        const baseHeight = 6;
        const maxHeight = 28;
        const range = maxHeight - baseHeight;

        // Create varied heights for natural wave look
        const multipliers = [0.6, 0.8, 1, 0.9, 1, 0.8, 0.6];

        return multipliers.map(m => {
            const height = baseHeight + (range * volume * m);
            return Math.max(baseHeight, Math.min(maxHeight, height));
        });
    }, [volume]);

    return (
        <div className={`voice-wave ${isActive ? 'active' : ''} ${isSpeaking ? 'speaking' : ''}`}>
            {barHeights.map((height, i) => (
                <div
                    key={i}
                    className="wave-bar"
                    style={{
                        height: `${height}px`,
                        transition: 'height 0.05s ease-out'
                    }}
                />
            ))}
        </div>
    );
});

