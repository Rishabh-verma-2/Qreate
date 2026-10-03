import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

import type {
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  User,
} from '../types';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach bearer token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('qreate_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log(`→ ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error normalization & auth handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token if invalid or expired
      localStorage.removeItem('qreate_token');
    }
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.message ||
      'An unexpected error occurred';
    console.error(`API Error: ${message}`, error.response?.data);
    return Promise.reject(new Error(message));
  }
);

// ── Projects ─────────────────────────────────────────────────────────────────
export const projectsApi = {
  list: () => api.get('/api/projects').then((r) => r.data.data),
  get: (id: string) => api.get(`/api/projects/${id}`).then((r) => r.data.data),
  create: (data: { name: string; topic: string; description?: string }) =>
    api.post('/api/projects', data).then((r) => r.data.data),
  delete: (id: string) => api.delete(`/api/projects/${id}`),
};

// ── Scripts ───────────────────────────────────────────────────────────────────
export const scriptsApi = {
  generate: (data: {
    project_id: string;
    topic: string;
    title?: string;
    duration_seconds?: number;
    language?: string;
    tone?: string;
    audience?: string;
    additional_instructions?: string;
  }) => api.post('/api/scripts/generate', data).then((r) => r.data.data),
  get: (id: string) => api.get(`/api/scripts/${id}`).then((r) => r.data.data),
  update: (id: string, data: Record<string, unknown>) =>
    api.put(`/api/scripts/${id}`, data).then((r) => r.data.data),
  regenerate: (id: string) =>
    api.post(`/api/scripts/${id}/regenerate`).then((r) => r.data.data),
};

// ── Videos ────────────────────────────────────────────────────────────────────
export const videosApi = {
  generate: (data: {
    project_id: string;
    script_id: string;
    mode?: string;
    duration_seconds?: number;
    aspect_ratio?: string;
    seed?: number;
    engine?: string;
  }) => api.post('/api/videos/generate', data).then((r) => r.data.data),
  getTask: (taskId: string) =>
    api.get(`/api/videos/tasks/${taskId}`).then((r) => r.data.data),
  list: () => api.get('/api/videos').then((r) => r.data.data),
  get: (id: string) => api.get(`/api/videos/${id}`).then((r) => r.data.data),
};

// ── Health ─────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/api/health').then((r) => r.data),
};

// ── Auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: RegisterCredentials): Promise<AuthResponse> =>
    api.post('/api/auth/register', data).then((r) => r.data?.data ?? r.data),
  login: (data: LoginCredentials): Promise<AuthResponse> =>
    api.post('/api/auth/login', data).then((r) => r.data?.data ?? r.data),
  me: (): Promise<User> =>
    api.get('/api/auth/me').then((r) => r.data?.data ?? r.data),
  logout: (): Promise<{ message: string }> =>
    api.post('/api/auth/logout').then((r) => r.data?.data ?? r.data),
};
