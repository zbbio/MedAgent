import type {
  AskRequest,
  AskResponse,
  AuthStatus,
  SystemHealth,
  SystemStats,
} from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;

  constructor(message: string, status: number, code = 'request_failed', requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = data?.error;
    throw new ApiError(
      error?.message || `请求失败 (${response.status})`,
      response.status,
      error?.code,
      error?.request_id,
    );
  }
  return data as T;
}

export async function askQuestion(request: AskRequest): Promise<AskResponse> {
  const data = await apiFetch<AskResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify(request),
  });

  let content = data.answer || '';
  let thinking = data.thinking || '';
  if (typeof content === 'string' && content.trim().startsWith('{')) {
    try {
      const parsed = JSON.parse(content);
      if (parsed.content) content = parsed.content;
      if (parsed.thinking && !thinking) thinking = parsed.thinking;
    } catch {
      // Keep the original answer when a model emits JSON-like plain text.
    }
  }
  return { ...data, answer: content, thinking };
}

export function login(password: string): Promise<AuthStatus> {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export function logout(): Promise<AuthStatus> {
  return apiFetch('/auth/logout', { method: 'POST' });
}

export function getAuthStatus(): Promise<AuthStatus> {
  return apiFetch('/auth/status');
}

export function getHealth(): Promise<SystemHealth> {
  return apiFetch('/health');
}

export function getStats(): Promise<SystemStats> {
  return apiFetch('/stats');
}
