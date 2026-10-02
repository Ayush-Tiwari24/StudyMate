import axios from 'axios';

const apiBaseUrl = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api`
  : '/api';

export function getToken() {
  return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
}

export function setTokens(accessToken, refreshToken, remember = true) {
  if (remember) {
    if (accessToken) localStorage.setItem('access_token', accessToken);
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
  } else {
    if (accessToken) sessionStorage.setItem('access_token', accessToken);
    if (refreshToken) sessionStorage.setItem('refresh_token', refreshToken);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

export function setToken(token, remember = true) {
  setTokens(token, null, remember);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
}

export async function refreshAuthToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearTokens();
    throw new Error('No refresh token available');
  }

  const response = await axios.post(`${apiBaseUrl}/auth/refresh`, {
    refresh_token: refreshToken,
  });

  const { access_token, refresh_token: new_refresh } = response.data;
  const isRemember = !!localStorage.getItem('access_token') || !!localStorage.getItem('refresh_token');
  setTokens(access_token, new_refresh, isRemember);
  return access_token;
}

const client = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-refresh token on 401 once, normalise errors & handle 429
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const data = error.response?.data;

    // 401 Auto-refresh single-retry logic
    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/register') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      originalRequest._retry = true;
      try {
        const newAccessToken = await refreshAuthToken();
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return client(originalRequest);
      } catch (refreshErr) {
        clearTokens();
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      }
    }

    let normalizedMessage = 'Something unexpected happened.';
    let errorCode = 'UNKNOWN';

    if (data?.error?.message) {
      normalizedMessage = data.error.message;
      errorCode = data.error.code || errorCode;
    } else if (data?.detail) {
      if (typeof data.detail === 'string') {
        normalizedMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        normalizedMessage = data.detail.map((d) => d.msg).join(', ');
      }
    }

    if (status === 401 && !originalRequest?._retry) {
      clearTokens();
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login';
      }
    } else if (status === 429) {
      normalizedMessage = "You're asking quickly. Try again in a moment.";
      errorCode = 'RATE_LIMIT';
    } else if (status === 409 && errorCode === 'DOCUMENT_NOT_READY') {
      normalizedMessage = data?.error?.message || 'This document is still being read. Please wait a moment.';
    } else if (status === 502 || status === 503 || status === 504 || data?.status === 'waking') {
      normalizedMessage = 'The database or server is waking up from sleep. Please wait a moment...';
      errorCode = 'SERVER_STARTING';

      // Auto-retry idempotent GET requests and login on cold start
      const isIdempotentOrLogin =
        (originalRequest?.method?.toLowerCase() === 'get' || originalRequest?.url?.includes('/auth/login')) &&
        !originalRequest?.url?.includes('/health');

      if (isIdempotentOrLogin && originalRequest) {
        originalRequest._coldStartRetries = (originalRequest._coldStartRetries || 0) + 1;
        if (originalRequest._coldStartRetries <= 2) {
          const delay = originalRequest._coldStartRetries * 1500;
          await new Promise((resolve) => setTimeout(resolve, delay));
          return client(originalRequest);
        }
      }

      window.dispatchEvent(
        new CustomEvent('backend-cold-start', {
          detail: { status, message: normalizedMessage },
        })
      );
    }

    // Attach normalised error properties
    error.normalized = {
      status,
      code: errorCode,
      message: normalizedMessage,
    };

    return Promise.reject(error);
  }
);

export default client;
