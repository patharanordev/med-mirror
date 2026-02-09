"use client";

import React from "react";

export function AudioWave({ isActive, audioData }: { isActive: boolean; audioData?: Uint8Array | null }) {
    // Select specific frequency bins for a balanced visual (Low, Mid, High)
    // 5 Bars. Indices from the 32-bin FFT. 
    // Adjusted to [0, 1, 2, 4, 6] to catch fundamental voice freqs (100Hz - 1kHz)
    const indices = [0, 1, 2, 4, 6];

    return (
        <div className={`audio-wave ${isActive ? "active" : ""}`}>
            {indices.map((idx, i) => {
                const value = audioData ? audioData[idx] || 0 : 0;
                // Dynamically scale height. Min height 6px. Max 40px.
                // value is 0-255.
                const height = isActive ? Math.max(6, (value / 255) * 48) : 6;

                return (
                    <div
                        key={i}
                        className="bar"
                        style={{
                            height: `${height}px`,
                            // slight transition for smoothness
                            transition: "height 0.05s ease-out"
                        }}
                    />
                );
            })}
            <style jsx>{`
        .audio-wave {
          display: flex;
          align-items: flex-end;
          justify-content: center;
          gap: 6px;
          height: 60px;
          transition: opacity 0.3s;
        }
        .audio-wave.active {
          opacity: 1;
        }
        .bar {
          width: 8px;
          background: #4ade80; /* Green-400 */
          border-radius: 9999px;
          box-shadow: 0 0 5px rgba(74, 222, 128, 0.4);
        }
        .audio-wave.active .bar {
            box-shadow: 0 0 12px rgba(74, 222, 128, 0.6);
        }
      `}</style>
        </div>
    );
}
