"use client";

import { useEffect, useRef, forwardRef, useImperativeHandle, useCallback } from "react";

const API_SEGMENTATION = "http://localhost:8000";

interface VideoFeedProps {
    onInference: (time: number, skinVal: number, image?: string) => void;
    isAutoMode: boolean;
}

export interface VideoFeedRef {
    toggleAuto: (active: boolean) => void;
    startCamera: () => Promise<void>;
    stopCamera: () => void;
    manualCapture: () => void;
}

export const VideoFeed = forwardRef<VideoFeedRef, VideoFeedProps>(
    ({ onInference, isAutoMode }, ref) => {
        const videoRef = useRef<HTMLVideoElement>(null);
        const canvasRef = useRef<HTMLCanvasElement>(null);
        const intervalRef = useRef<NodeJS.Timeout | null>(null);
        const isCapturingRef = useRef(false);

        const captureAndAnalyze = useCallback(async () => {
            if (!videoRef.current || videoRef.current.paused || isCapturingRef.current) return;

            isCapturingRef.current = true;
            const video = videoRef.current;
            const t0 = performance.now();

            const offscreen = document.createElement("canvas");
            offscreen.width = video.videoWidth;
            offscreen.height = video.videoHeight;
            const ctx = offscreen.getContext("2d");
            if (!ctx) {
                isCapturingRef.current = false;
                return;
            }
            // MIRROR FLIP: Translate and Scale
            ctx.save();
            ctx.translate(offscreen.width, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, 0, 0, offscreen.width, offscreen.height);
            ctx.restore();

            offscreen.toBlob(
                async (blob) => {
                    if (!blob) {
                        isCapturingRef.current = false;
                        return;
                    }

                    const formData = new FormData();
                    formData.append("file", blob, "frame.jpg");

                    try {
                        const res = await fetch(`${API_SEGMENTATION}/segment`, {
                            method: "POST",
                            body: formData,
                        });

                        if (!res.ok) throw new Error("Seg API Error");

                        // Parse JSON response with real skin analysis data
                        const data = await res.json();
                        const { skin_percentage, image: imageDataUrl } = data;

                        const displayCanvas = canvasRef.current;
                        if (displayCanvas) {
                            const displayCtx = displayCanvas.getContext("2d");
                            const img = new Image();
                            img.onload = () => {
                                displayCtx?.clearRect(0, 0, displayCanvas.width, displayCanvas.height);
                                displayCtx?.drawImage(img, 0, 0, displayCanvas.width, displayCanvas.height);
                            };
                            img.src = imageDataUrl;
                        }

                        const t1 = performance.now();
                        // Use real skin_percentage from the API instead of random value
                        onInference(t1 - t0, skin_percentage, imageDataUrl);
                    } catch (e) {
                        console.error("Segmentation Error:", e);
                    } finally {
                        isCapturingRef.current = false;
                    }
                },
                "image/jpeg",
                0.8
            );
        }, [onInference]);

        const startCamera = useCallback(async () => {
            if (!videoRef.current) return;
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        facingMode: "user",
                    },
                });
                videoRef.current.srcObject = stream;
                await videoRef.current.play();

                if (canvasRef.current && videoRef.current) {
                    canvasRef.current.width = videoRef.current.videoWidth;
                    canvasRef.current.height = videoRef.current.videoHeight;
                }
            } catch (err) {
                console.error("Camera access denied:", err);
                alert("Camera access denied. Please allow camera permissions.");
            }
        }, []);

        const stopCamera = useCallback(() => {
            if (videoRef.current?.srcObject) {
                const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
                tracks.forEach((t) => t.stop());
                videoRef.current.srcObject = null;
            }
            if (canvasRef.current) {
                const ctx = canvasRef.current.getContext("2d");
                ctx?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            }
        }, []);

        useImperativeHandle(ref, () => ({
            toggleAuto: () => { },
            startCamera,
            stopCamera,
            manualCapture: captureAndAnalyze,
        }), [startCamera, stopCamera, captureAndAnalyze]);

        useEffect(() => {
            if (isAutoMode) {
                intervalRef.current = setInterval(captureAndAnalyze, 2000); // 0.5 FPS like original
            } else {
                if (intervalRef.current) {
                    clearInterval(intervalRef.current);
                    intervalRef.current = null;
                }
            }

            return () => {
                if (intervalRef.current) {
                    clearInterval(intervalRef.current);
                }
            };
        }, [isAutoMode, captureAndAnalyze]);

        return (
            <>
                <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        opacity: 0.7, // Dimmed for legibility, matching original
                        transform: 'scaleX(-1)', // Mirror flip for live preview
                    }}
                />
                <canvas
                    ref={canvasRef}
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                    }}
                />
            </>
        );
    }
);

VideoFeed.displayName = "VideoFeed";
