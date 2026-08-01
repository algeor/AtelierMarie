/**
 * Typed fetch wrapper for communicating with the backend API.
 *
 * URL resolution:
 * - Browser (client) requests use NEXT_PUBLIC_API_URL — the publicly reachable
 *   origin (default: http://localhost:8000).
 * - Server-side requests (Server Components, route handlers) prefer
 *   API_INTERNAL_URL when set, so that in containerized/split deployments the
 *   server can reach the backend over the internal network (e.g.
 *   http://backend:8001) instead of a public origin that resolves to the
 *   frontend container's own loopback.
 *
 * API_INTERNAL_URL is NOT a NEXT_PUBLIC_ var: it is read only on the server and
 * is never bundled into client JavaScript.
 */

import type { ErrorResponse } from "./types";

const PUBLIC_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// On the server, prefer the internal URL when provided; fall back to the public
// one. In the browser, `process.env.API_INTERNAL_URL` is undefined (not a
// NEXT_PUBLIC_ var), so this always resolves to the public URL there.
const BASE_URL =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL || PUBLIC_BASE_URL
    : PUBLIC_BASE_URL;

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown> | null;

  constructor(response: ErrorResponse) {
    super(response.error.message);
    this.name = "ApiError";
    this.code = response.error.code;
    this.details = response.error.details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  // Detect session rotation on any response (even errors)
  if (res.headers.get("X-Session-Rotated") === "true") {
    window.dispatchEvent(new Event("session-rotated"));
  }

  if (!res.ok) {
    let body: ErrorResponse;
    try {
      const text = await res.text();
      const raw = JSON.parse(text);
      if (raw?.error?.message) {
        body = raw as ErrorResponse;
      } else {
        throw new Error("Unexpected error shape");
      }
    } catch {
      throw new ApiError({
        error: {
          code: "NETWORK_ERROR",
          message: `Request failed with status ${res.status}`,
          details: null,
        },
      });
    }
    throw new ApiError(body);
  }
  // 204 No Content — no body to parse.
  // Callers expecting no body should use del<void>(path) or patch<void>(path).
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return res.json() as Promise<T>;
}

// TODO: Add CSRF token to state-changing requests (POST/PATCH/DELETE).
// Implementation plan: backend sets a CSRF cookie (non-HttpOnly);
// this client reads it and sends it back in an X-CSRF-Token header.
// See: Double Submit Cookie pattern.
const DEFAULT_HEADERS: HeadersInit = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return handleResponse<T>(res);
}

export async function post<T>(
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function postForm<T>(
  path: string,
  body: FormData
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
    body,
  });
  return handleResponse<T>(res);
}

export async function patch<T>(
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    credentials: "include",
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function put<T>(
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    credentials: "include",
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  return handleResponse<T>(res);
}

// --- Reactions ---

import type {
  ReactionCountsResponse,
  ReactionToggleRequest,
  ReactionToggleResponse,
  CommentCreateRequest,
  CommentListResponse,
  CommentResponse,
  CommentSort,
  CalculateShippingRequest,
  CalculateShippingResponse,
} from "./types";

export async function toggleReaction(
  productId: string,
  body: ReactionToggleRequest
): Promise<ReactionToggleResponse> {
  return post<ReactionToggleResponse>(
    `/v1/products/${productId}/reactions`,
    body
  );
}

export async function getReactions(
  productId: string
): Promise<ReactionCountsResponse> {
  return get<ReactionCountsResponse>(
    `/v1/products/${productId}/reactions`
  );
}

// --- Comments ---

export async function postComment(
  productId: string,
  body: CommentCreateRequest
): Promise<CommentResponse> {
  return post<CommentResponse>(
    `/v1/products/${productId}/comments`,
    body
  );
}

export async function getComments(
  productId: string,
  sort: CommentSort = "newest",
  page: number = 1,
  limit: number = 20
): Promise<CommentListResponse> {
  return get<CommentListResponse>(
    `/v1/products/${productId}/comments?sort=${sort}&page=${page}&limit=${limit}`
  );
}

// --- Shipping ---

export async function calculateShipping(
  payload: CalculateShippingRequest
): Promise<CalculateShippingResponse> {
  return post<CalculateShippingResponse>("/v1/delivery/calculate", payload);
}

export { BASE_URL };