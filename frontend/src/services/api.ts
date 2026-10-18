const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export function token(): string | null {
  return localStorage.getItem("bc_token");
}

export async function api(path: string, options: RequestInit = {}): Promise<any> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    // If relative /api request failed (e.g. standalone preview or direct port), attempt direct backend
    if (BASE === "/api") {
      try {
        response = await fetch(`http://127.0.0.1:8000/api${path}`, { ...options, headers });
      } catch {
        throw new Error("Unable to connect to Blue Carbon API server. Please ensure the backend is running on http://127.0.0.1:8000.");
      }
    } else {
      throw new Error("Unable to connect to Blue Carbon API server. Please ensure the backend is running.");
    }
  }

  const data = await response.json().catch(() => ({ detail: response.statusText }));
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}: ${response.statusText}`);
  }
  return data;
}
