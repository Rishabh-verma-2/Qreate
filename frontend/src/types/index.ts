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
  camera_notes?: string;
}

export interface Script {
  id: string;
  project_id: string;
  title: string;
  hook?: string;
  closing?: string;
  scenes: Scene[];
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
  script_id: string;
  agnes_video_id?: string;
  status: VideoTaskStatus;
  progress: number;
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
  created_at: string;
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

export interface VideoGenerateForm {
  mode: 'text';
  duration_seconds: number;
  aspect_ratio: string;
  seed?: number;
}
