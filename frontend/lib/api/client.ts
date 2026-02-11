const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'compliance-ai-access-token';
const REFRESH_TOKEN_KEY = 'compliance-ai-refresh-token';

export class ApiError extends Error {
  constructor(public status: number, message: string, public details?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function clearTokensAndRedirect() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
    window.location.href = '/login?expired=true';
  }
}

// Prevent multiple concurrent refresh attempts
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return false;

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiRequest<T>(
  endpoint: string,
  options: { method?: string; body?: unknown; userId?: string } = {}
): Promise<T> {
  const headers: HeadersInit = { 'Content-Type': 'application/json' };

  // Use JWT token if available, otherwise fall back to userId header
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (options.userId) {
    headers['X-User-ID'] = options.userId;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  // On 401, try to refresh the token and retry once
  if (res.status === 401 && token) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const newToken = getAccessToken();
      const retryHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${newToken}`,
      };

      const retryRes = await fetch(`${API_BASE}${endpoint}`, {
        method: options.method || 'GET',
        headers: retryHeaders,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });

      if (retryRes.ok) {
        if (retryRes.status === 204) return null as T;
        return retryRes.json();
      }

      // Retry also failed — session is truly expired
      if (retryRes.status === 401) {
        clearTokensAndRedirect();
        throw new ApiError(401, 'Session expired. Please sign in again.');
      }

      const errorData = await retryRes.json().catch(() => ({}));
      throw new ApiError(retryRes.status, errorData.detail || `API error: ${retryRes.status}`, errorData);
    }

    // Refresh failed — redirect to login
    clearTokensAndRedirect();
    throw new ApiError(401, 'Session expired. Please sign in again.');
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorData.detail || `API error: ${res.status}`,
      errorData
    );
  }

  if (res.status === 204) {
    return null as T;
  }

  return res.json();
}

export async function uploadFile<T>(
  endpoint: string,
  file: File,
  userId?: string,
  additionalFields?: Record<string, string>
): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  if (additionalFields) {
    for (const [key, value] of Object.entries(additionalFields)) {
      if (value) {
        formData.append(key, value);
      }
    }
  }

  const headers: HeadersInit = {};

  // Use JWT token if available, otherwise fall back to userId header
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else if (userId) {
    headers['X-User-ID'] = userId;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  // On 401, try to refresh the token and retry once
  if (res.status === 401 && token) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const newToken = getAccessToken();
      const retryHeaders: HeadersInit = {
        'Authorization': `Bearer ${newToken}`,
      };

      const retryRes = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: retryHeaders,
        body: formData,
      });

      if (retryRes.ok) return retryRes.json();

      if (retryRes.status === 401) {
        clearTokensAndRedirect();
        throw new ApiError(401, 'Session expired. Please sign in again.');
      }

      const errorData = await retryRes.json().catch(() => ({}));
      throw new ApiError(retryRes.status, errorData.detail || 'Upload failed', errorData);
    }

    clearTokensAndRedirect();
    throw new ApiError(401, 'Session expired. Please sign in again.');
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      errorData.detail || 'Upload failed',
      errorData
    );
  }

  return res.json();
}
