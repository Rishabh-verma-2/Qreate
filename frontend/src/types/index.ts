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
  search_queries?: string[];
  camera_notes?: string;
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
  language: string;
  tone: string;
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
  timings?: Record<string, number>;
  created_at: string;
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
  tone: string;
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
  tone?: string;
  audience?: string;
  additional_instructions?: string;
}
