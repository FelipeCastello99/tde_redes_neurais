import { NextRequest, NextResponse } from "next/server";

// URL interna da API, lida em runtime (padrão localhost:8000 p/ desenvolvimento local)
const INTERNAL_API = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path: segments } = await params;
  const path = segments.join("/");
  const url = new URL(request.url);
  const search = url.search;
  
  try {
    const res = await fetch(`${INTERNAL_API}/api/${path}${search}`, {
      headers: {
        accept: request.headers.get("accept") || "application/json",
      },
    });
    
    // Tratamento para SSE (Server-Sent Events)
    if (res.headers.get("content-type")?.includes("text/event-stream")) {
      return new NextResponse(res.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
        },
      });
    }

    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    console.error("Erro no proxy:", error);
    return NextResponse.json({ detail: "API Backend indisponível" }, { status: 503 });
  }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path: segments } = await params;
  const path = segments.join("/");
  
  try {
    const body = await request.text();
    const res = await fetch(`${INTERNAL_API}/api/${path}`, {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("content-type") || "application/json",
        "Accept": "application/json",
      },
      body,
    });
    
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    console.error("Erro no proxy POST:", error);
    return NextResponse.json({ detail: "API Backend indisponível" }, { status: 503 });
  }
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path: segments } = await params;
  const path = segments.join("/");
  
  try {
    const res = await fetch(`${INTERNAL_API}/api/${path}`, {
      method: "DELETE",
    });
    
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    console.error("Erro no proxy DELETE:", error);
    return NextResponse.json({ detail: "API Backend indisponível" }, { status: 503 });
  }
}
