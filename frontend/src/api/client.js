import axios from 'axios';

const apiBaseUrl = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api`
  : '/api';

export function getToken() {
  return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

export function setToken(token, remember = true) {
  if (remember) {
    localStorage.setItem('access_token', token);
    sessionStorage.removeItem('access_token');
  } else {
    sessionStorage.setItem('access_token', token);
    localStorage.removeItem('access_token');
  }
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
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

// Response interceptor: normalise errors & handle 401 / 429
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const data = error.response?.data;

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

    if (status === 401) {
      clearTokens();
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login';
      }
    } else if (status === 429) {
      normalizedMessage = "You're asking quickly. Try again in a moment.";
      errorCode = 'RATE_LIMIT';
    } else if (status === 409 && errorCode === 'DOCUMENT_NOT_READY') {
      normalizedMessage = data?.error?.message || 'This document is still being read. Please wait a moment.';
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
