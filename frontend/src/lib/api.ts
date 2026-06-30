// Typed client for the CIdy backend.
import type {
  ArtifactDetail,
  ArtifactSummary,
  ArtifactValues,
  SchemaInfo,
  SDGSuggestion,
  TemplateSchema,
  UserInfo,
  ValidationReport,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

const TOKEN_KEY = "cidy.token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const t = tokenStore.get();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  }
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!resp.ok) {
    const detail =
      (data && (data.detail || data.message)) || `Request failed (${resp.status})`;
    throw new ApiError(resp.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

export const api = {
  // ---- auth ----
  requestMagicLink: (email: string) =>
    request<{ sent: boolean; dev_link: string | null }>(
      "POST",
      "/auth/magic-link",
      { email },
      false,
    ),
  verify: (token: string) =>
    request<{ access_token: string; token_type: string }>(
      "POST",
      "/auth/verify",
      { token },
      false,
    ),
  me: () => request<UserInfo>("GET", "/me"),

  // ---- schemas ----
  listSchemas: () => request<SchemaInfo[]>("GET", "/schemas"),
  getSchema: (id: string) => request<TemplateSchema>("GET", `/schemas/${id}`),

  // ---- artifacts ----
  listArtifacts: () => request<ArtifactSummary[]>("GET", "/artifacts"),
  createArtifact: (schema_id: string, title: string) =>
    request<ArtifactDetail>("POST", "/artifacts", { schema_id, title, content: {} }),
  getArtifact: (id: string) => request<ArtifactDetail>("GET", `/artifacts/${id}`),
  updateArtifact: (
    id: string,
    expected_version_no: number,
    title: string,
    content: ArtifactValues,
  ) =>
    request<ArtifactDetail>("PUT", `/artifacts/${id}`, {
      expected_version_no,
      title,
      content,
    }),
  checkArtifact: (id: string) =>
    request<ValidationReport>("POST", `/artifacts/${id}/check`),

  // ---- assist (LLM) ----
  shapeField: (id: string, section_id: string, field_id: string, raw_input: string) =>
    request<{ shaped_text: string }>("POST", `/artifacts/${id}/assist/shape`, {
      section_id,
      field_id,
      raw_input,
    }),
  coherence: (id: string) =>
    request<{ assessment: string }>("POST", `/artifacts/${id}/assist/coherence`),
  suggestSdg: (id: string) =>
    request<{ suggestions: SDGSuggestion[] }>("POST", `/artifacts/${id}/assist/sdg-suggest`),
};
