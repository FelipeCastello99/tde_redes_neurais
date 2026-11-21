export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(status: number, data: any) {
    super(data?.detail || "Erro na API");
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: await res.text() };
    }
    throw new ApiError(res.status, data);
  }
  return res.json() as Promise<T>;
}

export async function fetchMeta() {
  const res = await fetch("/api/meta");
  return handleResponse<any>(res);
}

export async function estimateRun(data: any, model: any) {
  const res = await fetch("/api/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data, model }),
  });
  return handleResponse<any>(res);
}

export async function createRun(name: string, data: any, model: any) {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, data, model }),
  });
  return handleResponse<any>(res);
}

export async function getRuns(limit = 20) {
  const res = await fetch(`/api/runs?limit=${limit}`);
  return handleResponse<any[]>(res);
}

export async function getRun(id: string) {
  const res = await fetch(`/api/runs/${id}`);
  return handleResponse<any>(res);
}

export async function cancelRun(id: string) {
  const res = await fetch(`/api/runs/${id}/cancel`, { method: "POST" });
  return handleResponse<any>(res);
}

export async function deleteRun(id: string) {
  const res = await fetch(`/api/runs/${id}`, { method: "DELETE" });
  return handleResponse<any>(res);
}

export async function predictAccident(runId: string, features: Record<string, string>) {
  const res = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, features }),
  });
  return handleResponse<any>(res);
}
