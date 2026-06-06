// Thin fetch wrapper around the passwordless OTP auth API.

const API_URL = import.meta.env.VITE_API_URL ?? "";
const PREFIX = `${API_URL}/api/v1`;

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: Tokens;
}

export interface OtpSentResponse {
  message: string;
  email: string;
  expires_in: number;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${PREFIX}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });

  const text = await res.text();
  const data = text ? JSON.parse(text) : {};

  if (!res.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail[0]?.msg ?? "Request failed"
          : "Request failed";
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const authApi = {
  register: (email: string, full_name: string) =>
    request<OtpSentResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name }),
    }),

  login: (email: string) =>
    request<OtpSentResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verify: (email: string, code: string) =>
    request<AuthResponse>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ email, code }),
    }),

  resend: (email: string) =>
    request<OtpSentResponse>("/auth/resend", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  me: (accessToken: string) =>
    request<User>("/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),

  logout: (refresh_token: string) =>
    request<{ message: string }>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),
};
