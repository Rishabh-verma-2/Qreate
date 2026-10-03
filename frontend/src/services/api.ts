import axios from 'axios';

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
    let message = 'An unexpected error occurred';
    const data = error.response?.data;
    if (typeof data?.error === 'string') {
      message = data.error;
    } else if (typeof data?.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail
        .map((d: any) => (typeof d === 'string' ? d : d?.msg || d?.message || 'Validation error'))
        .join('; ');
    } else if (data?.detail && typeof data.detail === 'object') {
      message = data.detail.msg || data.detail.message || JSON.stringify(data.detail);
    } else if (error.message) {
      message = error.message;
    }
    console.error(`API Error: ${message}`, data);
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
    tone?: string | string[];
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
