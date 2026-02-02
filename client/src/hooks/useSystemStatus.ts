"use client";

import { useState, useEffect } from "react";

const API_PROXY = "/api/proxy";
const POLL_INTERVAL = 3000; // Poll every 3 seconds

interface SystemStatus {
    stt: "loading" | "ready" | "error";
    llm: "loading" | "ready" | "error";
}

export function useSystemStatus() {
    const [status, setStatus] = useState<SystemStatus>({
        stt: "loading",
        llm: "loading",
    });

    useEffect(() => {
        let timeoutId: NodeJS.Timeout;
        let mounted = true;

        const checkStatus = async () => {
            try {
                const res = await fetch(`${API_PROXY}/health`); // GET /api/proxy/health
                if (!res.ok) throw new Error("Network error");

                const data = await res.json();

                if (mounted) {
                    setStatus({
                        stt: data.stt_ready ? "ready" : "loading",
                        llm: data.llm_ready ? "ready" : "loading",
                    });
                }
            } catch (e) {
                // Keep trying, maybe server is booting
                if (mounted) {
                    // Only set error if it persists? For now, sticky loading or error
                    // Actually, if fetch fails, agent might be down.
                    console.error("Health Check failed", e);
                }
            } finally {
                if (mounted) {
                    timeoutId = setTimeout(checkStatus, POLL_INTERVAL);
                }
            }
        };

        // Initial check
        checkStatus();

        return () => {
            mounted = false;
            clearTimeout(timeoutId);
        };
    }, []);

    return status;
}
