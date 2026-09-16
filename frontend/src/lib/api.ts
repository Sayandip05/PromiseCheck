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
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
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

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Transmit HttpOnly refresh cookie across origins
  });

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
    let errorMessage = 'An error occurred';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new ApiError(response.status, errorMessage);
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
    create: (data: { name: string; owner?: string }) =>
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
    disconnect: (provider: string) =>
      request<any>(`/integrations/${provider}/disconnect`, {
        method: 'POST',
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

