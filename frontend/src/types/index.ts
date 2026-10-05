// ── Domain types ─────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  topic: string;
  description?: string;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
  scripts?: Script[];
  video_tasks?: VideoTask[];
  generated_videos?: GeneratedVideo[];
}

export interface Scene {
  scene_number: number;
  duration_seconds: number;
  narration: string;
  visual_description: string;
  on_screen_text?: string;
  search_queries?: string[];
  camera_notes?: string;
  visual_type?: string;
  visual_subject?: string;
  visual_action?: string;
  visual_motion?: string;
  transition?: string;
  emphasis_words?: string[];
  pacing?: string;
  shot_type?: string;
  concept_key?: string;
}

export interface PostCopy {
  caption?: string;
  hashtags?: string[];
}

export interface Script {
  id: string;
  project_id: string;
  title: string;
  hook?: string;
  hook_text?: string;
  closing?: string;
  scenes: Scene[];
  music_mood?: string;
  post?: PostCopy;
  format?: string;
  angle?: string;
  research?: Inspiration & { top_shorts?: Inspiration['top_shorts'] };
  style?: Record<string, unknown>;
  language: string;
  tone: string | string[];
  audience?: string;
  duration_seconds: number;
  original_prompt?: string;
  additional_instructions?: string;
  approved: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export type VideoTaskStatus = 'pending' | 'queued' | 'in_progress' | 'completed' | 'failed';

export interface VideoTask {
  id: string;
  project_id: string;
  script_id?: string;
  batch_id?: string;
  topic?: string;
  title?: string;
  status: VideoTaskStatus;
  stage?: string;
  progress: number;
  attempts?: number;
  thumbnail_url?: string;
  error_message?: string;
  cloudinary_url?: string;
  generated_video_id?: string;
  generation_settings: {
    model?: string;
    mode?: string;
    duration_seconds?: number;
    aspect_ratio?: string;
    prompt_preview?: string;
  };
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface GeneratedVideo {
  id: string;
  project_id: string;
  script_id?: string;
  task_id?: string;
  cloudinary_url?: string;
  cloudinary_public_id?: string;
  original_url?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  file_format: string;
  title?: string;
  hook?: string;
  post?: PostCopy;
  credits?: string[];
  media_sources?: string[];
  inspiration?: Inspiration;
  timings?: Record<string, number>;
  created_at: string;
}

export interface Inspiration {
  niche?: string;
  emotion?: string;
  searches?: string[];
  news?: { title: string; source: string; date: string; url: string }[];
  top_shorts?: { title: string; views: number; url: string; channel?: string }[];
}

export interface BatchItem {
  task: VideoTask;
  video?: GeneratedVideo | null;
}

export interface Batch {
  id: string;
  name: string;
  topics: string[];
  task_ids: string[];
  options: Record<string, unknown>;
  created_at: string;
  items?: BatchItem[];
  summary?: { total: number; done: number; counts: Record<string, number> };
}

// ── Form types ─────────────────────────────────────────────────────────────────

export interface ScriptGenerateForm {
  topic: string;
  title?: string;
  duration_seconds: number;
  language: string;
  tone: string | string[];
  audience: string;
  additional_instructions?: string;
}

export interface UserMedia {
  url: string;
  kind: 'image' | 'video';
  duration?: number;
  name?: string;
}

export interface ContentOptions {
  title?: string;
  voice_gender?: 'male' | 'female';
  user_media?: UserMedia[];
  duration_seconds?: number;
  language?: string;
  tone?: string | string[];
  video_format?: string;
  visual_style?: string;
  color_theme?: string;
  accent_color?: string;
  caption_style?: string;
  voice_id?: string;
  pace?: string;
  music_mood?: string;
  people_focus?: boolean;
  audience?: string;
  additional_instructions?: string;
}

// ── Auth types ─────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name?: string | null;
  full_name?: string | null;
  is_active?: boolean;
  is_verified?: boolean;
  avatar?: string | null;
  avatar_url?: string | null;
  tier?: string;
  created_at?: string;
  last_login?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  name?: string;
  full_name?: string;
}

// ── AI Video Director types ──────────────────────────────────────────────────

export interface CameraInstruction {
  shot_type: string;
  movement: string;
  angle: string;
}

export interface VideoCharacter {
  id: string;
  name: string;
  description: string;
  appearance: string;
  clothing: string;
  style?: string;
  reference_image?: string;
}

export interface VideoPlanScene {
  id: string;
  duration: number;
  narration: string;
  visual_prompt: string;
  motion_prompt: string;
  camera: CameraInstruction;
  style: string;
  characters: string[];
  transition_in: string;
  transition_out: string;
  reference_image?: string;
  generated_clip_url?: string;
}

export interface AudioPlan {
  tts_voice?: string;
  music_mood?: string;
  sfx_notes?: string;
}

export interface VideoPlan {
  title: string;
  total_duration: number;
  style: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  fps: number;
  language: string;
  audio?: AudioPlan;
  characters: VideoCharacter[];
  scenes: VideoPlanScene[];
}

export interface VideoPlanRequest {
  prompt: string;
  style?: string;
  duration?: number;
  aspect_ratio?: '16:9' | '9:16' | '1:1';
  project_id?: string;
}

export interface WanGenerateRequest {
  project_id: string;
  prompt: string;
  style?: string;
  duration?: number;
  aspect_ratio?: '16:9' | '9:16' | '1:1';
  engine: 'wan';
  wan_mode?: 't2v' | 'i2v';
  quality?: 'development' | 'production';
  plan_id?: string;
  script_id?: string;
}

export interface WanVideoTask extends VideoTask {
  current_scene?: number;
  total_scenes?: number;
  video_plan?: VideoPlan;
}

export interface DiagnosticsResponse {
  gpu: {
    available: boolean;
    cuda: boolean;
    gpu_name: string | null;
    vram_gb: number | null;
    warning: string | null;
  };
  qwen: {
    available: boolean;
    base_url: string;
    model: string;
    warning: string | null;
    models?: string[];
  };
  comfyui: {
    available: boolean;
    base_url: string;
    warning: string | null;
  };
  wan: {
    available: boolean;
    mode: string;
    model_size: string;
    model_path: string;
    warning: string | null;
  };
  warnings: string[];
  video_engine_ready: boolean;
  llm_ready: boolean;
}

