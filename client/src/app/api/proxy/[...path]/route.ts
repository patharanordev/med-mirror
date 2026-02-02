import { NextRequest, NextResponse } from "next/server";

// Force Node.js runtime for proper streaming and env var access
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic'; // Disable static optimization/buffering

/**
 * Explicit Proxy Handler for Local Agent Service.
 * Routes: /api/proxy/[...path] -> http://med_mirror_agent:8001/[...path]
 */
async function handler(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
    // 1. Resolve Target URL
    // Environment variable injected by docker-compose
    const AGENT_URL = process.env.AGENT_SERVICE_URL || "http://localhost:8001";

    // Await params for Next.js 15+ compatibility
    const resolvedParams = await params;

    // Safety check for empty path if accessed via /api/proxy (though [...path] usually requires segments)
    const pathJoined = resolvedParams.path?.join("/") || "";
    const targetUrl = `${AGENT_URL}/${pathJoined}`;

    console.log(`[Proxy] Forwarding ${req.method} request to: ${targetUrl}`);

    try {
        // 2. Prepare Request Options
        const headers = new Headers(req.headers);
        headers.delete("host");
        headers.delete("connection");

        // 3. fetch upstream
        const response = await fetch(targetUrl, {
            method: req.method,
            headers: headers,
            body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
            // @ts-ignore
            duplex: req.body ? "half" : undefined,
        });

        console.log(`[Proxy] Response status: ${response.status}`);

        // 4. Return Response with SSE Headers forced
        const resHeaders = new Headers(response.headers);
        resHeaders.set("Cache-Control", "no-cache, no-transform");
        resHeaders.set("Connection", "keep-alive");

        return new NextResponse(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: resHeaders,
        });

    } catch (error) {
        console.error("[Proxy] Error:", error);
        return NextResponse.json(
            { error: "Proxy Failed", details: String(error) },
            { status: 502 }
        );
    }
}

// Support all HTTP methods
export { handler as GET, handler as POST, handler as PUT, handler as DELETE, handler as PATCH };
