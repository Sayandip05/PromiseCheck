/**
 * PromiseCheck API Client
 * Production-grade typed HTTP client with JWT Bearer authentication,
 * token storage, and transparent 401 auto-refresh token rotation.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface WorkspaceContext {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface UserMeResponse extends UserProfile {
  active_workspace: WorkspaceContext | null;
  workspaces: WorkspaceContext[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
  active_workspace: WorkspaceContext | null;
  workspaces: WorkspaceContext[];
}

export interface AuthRegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthLoginPayload {
  email: string;
  password: string;
}

export interface GoogleAuthPayload {
  email?: string;
  full_name?: string;
  credential?: string;
  id_token?: string;
}

export class ApiError extends Error {
  status: number;
  rawDetail?: any;
  userMessage: string;

  constructor(status: number, message: string, rawDetail?: any) {
    super(message);
    this.status = status;
    this.rawDetail = rawDetail;
    this.userMessage = message;
    this.name = 'ApiError';
  }
}

/**
 * Translates raw backend HTTP and Pydantic validation errors into
 * plain, friendly, and actionable explanations for users.
 */
export function formatApiErrorMessage(
  status: number,
  errorData: any,
  statusText?: string
): string {
  // 1. Connection / Network failure (status = 0 or aborted)
  if (status === 0) {
    return 'Unable to connect to PromiseCheck. Please check your internet connection and verify that the backend server is running.';
  }

  // 2. Extract error payload detail if present
  const detail = errorData?.detail ?? errorData?.message ?? errorData?.error;

  // Case A: FastAPI / Pydantic validation error array (status 422 or 400)
  if (Array.isArray(detail) && detail.length > 0) {
    const errorItems = detail.map((item: any) => {
      if (typeof item === 'string') return item;
      const rawLoc = Array.isArray(item?.loc) ? item.loc : [];
      // Get the leaf field name (ignore 'body', 'query', etc.)
      const field = rawLoc
        .filter((p: any) => p !== 'body' && p !== 'query' && p !== 'path')
        .pop();
      const fieldLabel = field
        ? String(field)
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (char) => char.toUpperCase())
        : 'Input';

      let msg = item?.msg || item?.message || 'is invalid';
      if (typeof msg === 'string') {
        if (msg.startsWith('value is not a valid ')) {
          msg = `Please provide a valid ${msg.replace('value is not a valid ', '')}`;
        } else if (msg === 'Field required') {
          msg = 'This field is required';
        }
      }

      return `${fieldLabel}: ${msg}`;
    });

    return `Please check your input:\n• ${errorItems.join('\n• ')}`;
  }

  // Case B: Detail is a structured object
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.error === 'string') return detail.error;
    if (typeof detail.msg === 'string') return detail.msg;
  }

  // Case C: Detail is a plain string
  if (typeof detail === 'string' && detail.trim().length > 0) {
    let cleanDetail = detail.trim();
    // Strip technical prefixes if present
    cleanDetail = cleanDetail.replace(/^(error:\s*|exception:\s*|\[.*?\]:\s*)/i, '');
    return cleanDetail;
  }

  // Case D: Fallback to contextual human explanation based on HTTP status
  switch (status) {
    case 400:
      return 'The request could not be completed. Please review the submitted details.';
    case 401:
      return 'Your session has expired or you are not signed in. Please log in again to continue.';
    case 403:
      return 'Access restricted: You do not have permission to perform this action in this workspace.';
    case 404:
      return 'The requested resource or integration could not be found.';
    case 408:
      return 'The request timed out. Please try again.';
    case 409:
      return 'A conflict occurred. A record with this information already exists.';
    case 413:
      return 'File size exceeds the 200 MB maximum limit. Please upload a smaller file.';
    case 422:
      return 'Some form fields contain invalid information. Please review and try again.';
    case 429:
      return 'Too many requests. Please wait a moment before trying again.';
    case 500:
      return 'The server encountered an unexpected error. Please try again in a few moments.';
    case 502:
    case 503:
    case 504:
      return 'External service or gateway is temporarily unavailable. Please verify your integration credentials and try again.';
    default:
      return statusText || 'An unexpected error occurred. Please try again.';
  }
}

/**
 * Convenience helper to extract a friendly error message from any caught error.
 */
export function explainError(error: unknown, fallback = 'An unexpected error occurred.'): string {
  if (!error) return fallback;
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message || fallback;
  if (typeof error === 'string') return error;
  if (typeof error === 'object' && 'message' in (error as any)) {
    return String((error as any).message);
  }
  return fallback;
}

// In-memory token storage with localStorage persistence for browser tabs
let inMemoryAccessToken: string | null = null;
try {
  inMemoryAccessToken = localStorage.getItem('promisecheck_access_token');
} catch {}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null) {
  inMemoryAccessToken = token;
  try {
    if (token) {
      localStorage.setItem('promisecheck_access_token', token);
    } else {
      localStorage.removeItem('promisecheck_access_token');
    }
  } catch {}
}

// Single-flight refresh token queue to prevent race conditions on concurrent 401s
let refreshPromise: Promise<TokenResponse> | null = null;

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  isRetry = false
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach JWT Bearer Authorization header if access token exists
  const token = getAccessToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Transmit HttpOnly refresh cookie across origins
    });
  } catch (networkErr: any) {
    throw new ApiError(
      0,
      'Unable to connect to PromiseCheck server. Please check your network connection or verify that the backend is active.',
      networkErr
    );
  }

  // Transparent 401 Auto-Refresh Interceptor
  if (
    response.status === 401 &&
    !isRetry &&
    !endpoint.includes('/auth/login') &&
    !endpoint.includes('/auth/register') &&
    !endpoint.includes('/auth/refresh')
  ) {
    try {
      if (!refreshPromise) {
        refreshPromise = api.auth.refresh().finally(() => {
          refreshPromise = null;
        });
      }
      const tokenData = await refreshPromise;
      setAccessToken(tokenData.access_token);

      // Retry original request with newly issued access token
      return request<T>(endpoint, options, true);
    } catch {
      setAccessToken(null);
      // Let original error propagate
    }
  }

  if (!response.ok) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      // Body is not JSON
    }
    const friendlyMessage = formatApiErrorMessage(
      response.status,
      errorData,
      response.statusText
    );
    throw new ApiError(response.status, friendlyMessage, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  auth: {
    register: async (data: AuthRegisterPayload): Promise<TokenResponse> => {
      const res = await request<TokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setAccessToken(res.access_token);
      return res;
    },

    login: async (data: AuthLoginPayload): Promise<TokenResponse> => {
      const res = await request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setAccessToken(res.access_token);
      return res;
    },

    refresh: async (refreshToken?: string): Promise<TokenResponse> => {
      const res = await request<TokenResponse>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
      });
      setAccessToken(res.access_token);
      return res;
    },

    google: async (data: GoogleAuthPayload): Promise<TokenResponse> => {
      const res = await request<TokenResponse>('/auth/google', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      setAccessToken(res.access_token);
      return res;
    },

    me: (): Promise<UserMeResponse> => request<UserMeResponse>('/auth/me'),

    logout: async (): Promise<{ status: string }> => {
      try {
        return await request<{ status: string }>('/auth/logout', {
          method: 'POST',
        });
      } finally {
        setAccessToken(null);
      }
    },
  },

  commitments: {
    list: (params?: { status?: string; category?: string; search?: string }) => {
      const query = new URLSearchParams();
      if (params?.status) query.set('status', params.status);
      if (params?.category) query.set('category', params.category);
      if (params?.search) query.set('search', params.search);
      const qs = query.toString() ? `?${query.toString()}` : '';
      return request<any[]>(`/commitments${qs}`);
    },
    create: (data: any) =>
      request<any>('/commitments', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: any) =>
      request<any>(`/commitments/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    confirm: (id: string) =>
      request<any>(`/commitments/${id}/confirm`, {
        method: 'POST',
      }),
    draftUpdate: (id: string, data?: { recipient_name?: string }) =>
      request<any>(`/commitments/${id}/draft-update`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),
    delete: (id: string) =>
      request<{ status: string; id: string }>(`/commitments/${id}`, {
        method: 'DELETE',
      }),
  },

  customers: {
    list: () => request<any[]>('/customers'),
    create: (data: { name: string; owner?: string; recent_promise?: string; due_date?: string }) =>
      request<any>('/customers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  integrations: {
    list: () => request<any[]>('/integrations'),
    connect: (provider: string, data?: any) =>
      request<any>(`/integrations/${provider}/connect`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),
    test: (provider: string, data?: any) =>
      request<{ success: boolean; provider: string; message: string; details?: any }>(
        `/integrations/${provider}/test`,
        {
          method: 'POST',
          body: JSON.stringify(data || {}),
        }
      ),
    disconnect: (provider: string) =>
      request<any>(`/integrations/${provider}/disconnect`, {
        method: 'POST',
      }),
    getGoogleAuthorizeUrl: (redirectUri?: string) =>
      request<{ authorization_url: string; redirect_uri: string; state: string }>(
        `/integrations/google/authorize${redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''}`
      ),
    connectGoogleToken: (data: {
      access_token: string;
      refresh_token?: string;
      email?: string;
      expires_in?: number;
    }) =>
      request<any>('/integrations/google/connect-token', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    syncCalendarEvent: (data: {
      commitment_id?: string;
      title: string;
      due_date_iso: string;
      description?: string;
    }) =>
      request<{ status: string; email?: string; event?: any; html_link?: string }>(
        '/integrations/google/calendar/sync-event',
        {
          method: 'POST',
          body: JSON.stringify(data),
        }
      ),
    sendGmailUpdate: (data: {
      to_email: string;
      subject: string;
      body: string;
      commitment_id?: string;
    }) =>
      request<{ status: string; sender?: string; result?: any }>(
        '/integrations/google/gmail/send-update',
        {
          method: 'POST',
          body: JSON.stringify(data),
        }
      ),
  },

  notifications: {
    send: (data: {
      channel: string;
      recipient?: string;
      message: string;
      commitment_id?: string;
    }) =>
      request<any>('/notifications/send', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  audit: {
    list: () => request<any[]>('/audit'),
  },

  ingestion: {
    upload: (data: {
      customer?: string;
      meeting_title?: string;
      transcript_text?: string;
      source_type?: string;
    }) =>
      request<any>('/ingestion/upload', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    jobs: () => request<any[]>('/ingestion/jobs'),
  },

  mcp: {
    tools: () => request<{ tools: any[] }>('/mcp/tools'),
    call: (name: string, args: Record<string, any> = {}) =>
      request<{ content: any[]; isError: boolean }>('/mcp/tools/call', {
        method: 'POST',
        body: JSON.stringify({ name, arguments: args }),
      }),
  },

  workspaces: {
    get: (workspaceId: string) => request<any>(`/workspaces/${workspaceId}`),
    members: (workspaceId: string) =>
      request<any[]>(`/workspaces/${workspaceId}/members`),
  },
};

