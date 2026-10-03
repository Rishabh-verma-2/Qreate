import axios from 'axios';
import type { ContentOptions, UserMedia } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request logging
api.interceptors.request.use((config) => {
  console.log(`→ ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error normalization
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.error ||
      error.response?.data?.detail ||
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
  generate: (data: ContentOptions & {
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
  generate: (data: { project_id: string; script_id: string }) =>
    api.post('/api/videos/generate', data).then((r) => r.data.data),
  getTask: (taskId: string) =>
    api.get(`/api/videos/tasks/${taskId}`).then((r) => r.data.data),
  list: () => api.get('/api/videos').then((r) => r.data.data),
  get: (id: string) => api.get(`/api/videos/${id}`).then((r) => r.data.data),
};

// ── Pipeline (one-shot + batch) ───────────────────────────────────────────────
export const pipelineApi = {
  run: (data: ContentOptions & { topic: string }) =>
    api.post('/api/pipeline/run', data).then((r) => r.data.data),
  queueStats: () => api.get('/api/queue/stats').then((r) => r.data.data),
};

export const batchesApi = {
  create: (data: { name?: string; topics: string[]; options: ContentOptions }) =>
    api.post('/api/batches', data).then((r) => r.data.data),
  list: () => api.get('/api/batches').then((r) => r.data.data),
  get: (id: string) => api.get(`/api/batches/${id}`).then((r) => r.data.data),
};

// ── Uploads (creator's own photos/videos) ──────────────────────────────────────
export const uploadsApi = {
  upload: (files: File[]): Promise<UserMedia[]> => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    return api
      .post('/api/uploads', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 300000 })
      .then((r) => r.data.data);
  },
};

// ── Health ─────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get('/api/health').then((r) => r.data),
};
