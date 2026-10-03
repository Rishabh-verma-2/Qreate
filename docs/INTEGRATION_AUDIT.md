# 🔍 Qreate + PurffleShorts Integration Audit

**Date:** 2026-10-03  
**Status:** Phase 0 Completed — System Audited  
**Repository:** `Rishabh-verma-2/Qreate`  
**Current Commit:** `487d07639f240cd48f522e19f64f7e2ab2a1c385`  
**Branch:** `main` (Clean working tree)  

---

## 1. Executive Summary

This audit assesses the current architecture of **Qreate** to prepare for the seamless addition of **PurffleShorts** as an integrated video-generation engine alongside Qreate's existing **Native Free Engine** and **Agnes AI Cloud Engine**, and the addition of **Ollama** as a local LLM provider for script generation.

### Core Principles
1. **Qreate is the product; PurffleShorts is an integrated engine.**
2. **Zero regression:** Existing Native Free and Agnes Cloud engines remain intact and operational.
3. **No destructive changes:** MongoDB Atlas persistence, Cloudinary CDN asset pipelines, React 19 frontend layout, and FastAPI backend routes are strictly preserved.
4. **VRAM and hardware safety:** Targeted for RTX 4060 Laptop (8 GB VRAM, 24 GB RAM). No heavyweight models (5 GB+) downloaded without prior evaluation and consent.

---

## 2. Existing Qreate Architecture

### 2.1 Frontend Architecture
* **Stack:** React 19, TypeScript, Vite, TailwindCSS, Lucide React, Axios, React Router DOM v7.
* **Routing:**
  * `/` — Landing page.
  * `/app` — Dashboard with stats and quick actions.
  * `/app/create` — `CreateVideo.tsx` (Project & Script generation initiation).
  * `/app/scripts/:scriptId/edit` — `ScriptEditor.tsx` (Interactive scene editor, scene regeneration).
  * `/app/scripts/:scriptId/generate` — `GenerateVideo.tsx` (Engine selection, aspect ratio, duration, polling progress bar, video player).
  * `/app/projects` & `/app/projects/:id` — Project details, script list, task history.
  * `/app/videos` — VideoLibrary grid and preview.
* **API Client (`frontend/src/services/api.ts`):**
  * Axios client pointing to `VITE_API_BASE_URL` (default `http://localhost:8000`).
  * `scriptsApi`: `generate`, `get`, `update`, `regenerate`.
  * `videosApi`: `generate` (accepts `engine: 'auto' | 'free' | 'agnes'`), `getTask`, `list`, `get`.
* **Engine Selection in UI:**
  * `GenerateVideo.tsx` currently provides an `ENGINE_OPTIONS` selector:
    * `free`: ⚡ Free AI Multi-Scene Engine (Neural Voice + Visuals — 100% Free)
    * `auto`: 🔄 Auto (Try Agnes AI, fallback to Free Engine if rate-limited)
    * `agnes`: 🤖 Agnes Video Generator (Requires Token Plan on Agnes)
  * Can be extended cleanly with `purffle`: 🎬 PurffleShorts Local Engine (Word-synced Captions, 9:16 Shorts Autopilot).

### 2.2 Backend Architecture
* **Stack:** FastAPI, Uvicorn, Pydantic v2 + Pydantic Settings, Motor (Async MongoDB), Cloudinary SDK, Edge-TTS, ImageIO-FFmpeg, Pillow.
* **Entry Point (`backend/app/main.py`):**
  * Configures CORS middleware.
  * Global exception handlers (`QreateError`, generic exceptions).
  * Lifecycle startup/shutdown connecting to MongoDB.
  * Routers: `/api/health`, `/api/projects`, `/api/scripts`, `/api/videos`.
* **Config (`backend/app/core/config.py`):**
  * Pydantic settings loading from `backend/.env`.
  * Configures MongoDB URI, Cloudinary keys, Agnes credentials, polling timeouts.

### 2.3 Database Layer (`backend/app/database/`)
* **Driver:** `motor.motor_asyncio.AsyncIOMotorClient` + `pymongo`.
* **Collections & Indexes:**
  1. `projects` — `id`, `name`, `topic`, `description`, `status`, `created_at`, `updated_at`.
  2. `scripts` — `id`, `project_id`, `title`, `hook`, `closing`, `scenes`, `language`, `tone`, `audience`, `duration_seconds`, `original_prompt`, `approved`, `version`, `created_at`, `updated_at`.
  3. `video_tasks` — `id`, `project_id`, `script_id`, `agnes_video_id`, `status` (`pending` | `queued` | `in_progress` | `completed` | `failed`), `progress` (0–100), `error_message`, `generation_settings`, `created_at`, `updated_at`, `completed_at`.
  4. `generated_videos` — `id`, `project_id`, `script_id`, `task_id`, `cloudinary_url`, `cloudinary_public_id`, `original_url`, `thumbnail_url`, `duration_seconds`, `file_format`, `created_at`.
* **Resilience:** Graceful offline fallback in `crud.py` if MongoDB is disconnected (`{"id": "offline", ...}`).

### 2.4 Cloudinary Storage (`backend/app/services/cloudinary/uploader.py`)
* Provides:
  * `upload_video_from_url(video_url, project_id, task_id)` — for cloud outputs.
  * `upload_video_file(file_path, project_id, task_id)` — for local MP4 files.
  * `delete_video(public_id)`.
* Returns `(secure_url, public_id)` with graceful fallback if credentials are unset.

---

## 3. Existing Script Generation Flow

### 3.1 Current Implementation
* **Route:** `POST /api/scripts/generate` and `POST /api/scripts/{id}/regenerate`.
* **Service:** `app/services/script/generator.py`:
  1. Prepares `SCRIPT_SYSTEM_PROMPT` instructing the LLM to output pure JSON.
  2. Directly calls `AgnesClient.chat_completion()` using Agnes model `agnes-2.5-flash`.
  3. Parses response with `_parse_script_response()` (handles markdown code fence cleanup and regex JSON extraction).
  4. Normalizes scene structure:
     ```json
     {
       "title": "...",
       "total_duration_seconds": 60,
       "hook": "...",
       "closing": "...",
       "scenes": [
         {
           "scene_number": 1,
           "duration_seconds": 10,
           "narration": "...",
           "visual_description": "...",
           "camera_notes": "..."
         }
       ]
     }
     ```
  5. Stores script in MongoDB and returns created document.

### 3.2 Ollama Integration Point
* **Decoupling:** `generator.py` currently has a hard dependency on `AgnesClient`.
* **Target Architecture:** Introduce an LLM Provider interface:
  * `BaseLLMProvider` (abstract class with `chat_completion`)
  * `AgnesLLMProvider` (wraps existing Agnes chat logic)
  * `OllamaLLMProvider` (communicates with local Ollama at `http://localhost:11434` using native API or OpenAI-compatible endpoint)
* **Configuration:** Controlled by `LLM_PROVIDER` in settings (`agnes` | `ollama`), defaulting seamlessly to current provider when configured, or auto-detecting Ollama if local free mode is requested.

---

## 4. Existing Video Generation & Task Flow

### 4.1 Video Generation Flow
* **Route:** `POST /api/videos/generate` (status 202 Accepted).
* **Workflow:**
  1. Validates `project_id` and `script_id`.
  2. Deduplicates: checks for existing in-progress tasks (`pending`, `queued`, `in_progress`).
  3. Flattens script into video prompt preview with `script_to_video_prompt(script)`.
  4. Creates `video_tasks` record in MongoDB with `progress: 0, status: "pending"`.
  5. Dispatches background task: `_run_video_generation()`.
  6. Returns `VideoTaskResponse` immediately to frontend.

### 4.2 Engine Routing (`_run_video_generation`)
* Current routes:
  * `engine == "free"`: Directly calls `_generate_via_free_engine()`.
  * `engine == "agnes"` or `engine == "auto"`:
    1. Submits video generation task to Agnes API (`create_video_task`).
    2. Polls Agnes status endpoint every `VIDEO_POLL_INTERVAL_SECONDS` (10s) up to `VIDEO_POLL_MAX_ATTEMPTS`.
    3. Once completed: calls `sync_audio_and_captions_to_video()` to add Edge-TTS voiceover and burned subtitles over the Agnes visual.
    4. Auto-fallback: If Agnes returns `503 Queue Full` or fails, catches `(AgnesAPIError, AgnesQueueFullError)` and falls back to `_generate_via_free_engine()`.

### 4.3 Native Free Engine (`backend/app/services/video_engine/free_generator.py`)
* Fully local/free multi-scene synthesis pipeline:
  1. **Voiceover & Subtitles:** `edge_tts.Communicate` generates audio and calculates millisecond-level word/sentence boundaries to emit an SRT subtitle file.
  2. **Scene Visuals:** `fetch_scene_image` queries Pollinations.ai or Unsplash stock photo topics (`food`, `general`) with a local canvas fallback.
  3. **Cinematic Motion:** `render_scene_clip` runs `imageio_ffmpeg` with Ken Burns zoom/pan filter expressions (`zoompan`) and burns in SRT subtitles via libass filter.
  4. **Multi-scene Concatenation:** `concat_scene_clips` joins clips using FFmpeg `-filter_complex concat`.
  5. **Cloud Upload:** Calls `upload_video_file` to upload the final assembled MP4 to Cloudinary and saves metadata to MongoDB.

### 4.4 Task Polling (`GET /api/videos/tasks/{task_id}`)
* Returns the task object including `status`, `progress` (0–100), `error_message`, and `cloudinary_url`.
* Frontend polls every 4000ms until status is `completed` or `failed`.

---

## 5. PurffleShorts Integration Analysis

### 5.1 What PurffleShorts Provides
* Open-source automated 9:16 vertical video engine:
  * Uses `edge-tts` for word-accurate narration and multi-speaker dialogues.
  * Formats: explainer, facts, story, dialogue, chat stories, reddit posts.
  * Subtitles: 6 word-by-word highlighted caption styles (pop-in, karaoke, bold, boxed, etc.) via PIL/FFmpeg overlays.
  * Footage/visuals: Pexels/Pixabay stock footage, Pollinations/DALL-E images, local background assets.
  * Assembly: Pure FFmpeg pipeline, auto-ducking background music, −14 LUFS normalization.
  * CLI support: `purffle-shorts make --script <script.json> --no-upload --aspect 9:16`.

### 5.2 Integration Strategy Options
* **Option A:** Install PurffleShorts package into the Python virtual environment and call Python API (`Studio(settings).make(...)`).
* **Option B:** Keep PurffleShorts as an integrated or sibling engine and invoke its CLI via a subprocess runner.
* **Option C:** Selective copy of internal modules.

### 5.3 Recommendation: Option B / Controlled Subprocess Adapter
* **Why:**
  1. **Strict Failure Isolation:** Purffle runs in its own process. If an FFmpeg filter, external network call, or memory spike fails, the FastAPI server process is completely immune from crashes.
  2. **CLI Stability:** Purffle's CLI (`make --script <json_path> --no-upload`) is explicitly designed as a self-contained command with stdout progress logging.
  3. **Modular Adapter (`backend/app/services/purffle/`):**
     * Hides all Purffle execution details.
     * Takes Qreate's native `Script` schema, converts it into Purffle's JSON schema (`topic`, `title`, `hook_text`, `scenes: [{speaker, narration, search_query, image_prompt}]`).
     * Writes to a temporary job directory, executes the runner, parses progress milestones, validates the generated MP4, and hands it off to Qreate's Cloudinary uploader.

---

## 6. Ollama Local LLM Analysis

### 6.1 Current Status
* `ollama --version`: **`0.35.1`** (Installed and active on Windows).
* `ollama list`: Currently empty (no models installed).
* `http://localhost:11434`: Verified running and accessible.

### 6.2 Target Model Evaluation
* **Target Model:** `qwen3:8b` (or `qwen2.5:7b` / `qwen2.5:8b` pending exact registry tag).
* **Hardware Profile:**
  * GPU: NVIDIA GeForce RTX 4060 Laptop GPU (8 GB GDDR6 VRAM).
  * System RAM: 24 GB DDR5.
  * Disk: NVMe SSD.
* **Model Profile (Qwen 8B / 7B Q4_K_M quant):**
  * Download Size: ~4.7 GB.
  * VRAM footprint: ~5.2–5.8 GB (Fits completely inside 8 GB VRAM).
  * Context window: 4K–8K tokens for short script generation is lightweight.
* **Model Safety Protocol:** Will be pulled only during Milestone 3/6 after explicit verification.

---

## 7. Files Impact Assessment

### Files to Modify
| File | Rationale | Scope of Change |
|---|---|---|
| `backend/app/core/config.py` | Add Purffle and Ollama config settings | Minimal additions (`LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `PURFFLE_EXECUTABLE_PATH`). Preserves all existing defaults. |
| `backend/app/schemas/schemas.py` | Allow `purffle` in `VideoGenerateRequest.engine` enum / pattern | Extend pattern `^(auto\|free\|agnes\|purffle)$`. Preserves all other schema structures. |
| `backend/app/services/script/generator.py` | Support pluggable LLM provider (Agnes vs. Ollama) | Refactor into provider interface; existing Agnes logic untouched. |
| `backend/app/api/routes/videos.py` | Route `engine == "purffle"` to Purffle runner | Add branch in `_run_video_generation` without touching Agnes or Free engine branches. |
| `frontend/src/pages/GenerateVideo.tsx` | Add Purffle option to engine dropdown | Add `{ value: 'purffle', label: '🎬 PurffleShorts Local Engine (9:16 Shorts Autopilot)' }` to `ENGINE_OPTIONS`. |
| `frontend/src/types/index.ts` | Update TypeScript type for video engines | Add `'purffle'` to accepted engine values. |

### New Files to Create
| File | Purpose |
|---|---|
| `backend/app/services/script/providers/base.py` | Abstract Base Class for LLM script providers. |
| `backend/app/services/script/providers/agnes.py` | Existing Agnes chat provider encapsulation. |
| `backend/app/services/script/providers/ollama.py` | Ollama HTTP/JSON script provider. |
| `backend/app/services/purffle/__init__.py` | Purffle adapter package entry. |
| `backend/app/services/purffle/adapter.py` | Converts Qreate script to Purffle JSON schema. |
| `backend/app/services/purffle/runner.py` | Subprocess runner executing Purffle with stdout progress tracking. |
| `backend/app/services/purffle/schemas.py` | Pydantic definitions for Purffle script format. |
| `backend/app/services/purffle/errors.py` | Specific Purffle execution exception classes. |

### Files That Must NOT Be Modified
* `backend/app/services/video_engine/free_generator.py` (Native Free Engine — preserve completely).
* `backend/app/services/agnes/client.py` (Agnes API Client — preserve completely).
* `backend/app/services/cloudinary/uploader.py` (Cloudinary service — preserve completely).
* `backend/app/database/connection.py` & `crud.py` (Database layer — preserve completely).
* `frontend/src/components/*` (Core UI component kit — preserve completely).
* `frontend/src/layouts/*` (Layouts — preserve completely).

---

## 8. Concrete Risks & Mitigation Strategies

1. **Risk: FFmpeg libass / Subtitle Filter Failure on Windows.**
   * *Mitigation:* Ensure bundled `imageio-ffmpeg` or validated FFmpeg binary path with fontconfig/libass support is supplied to Purffle, with fallbacks matching Qreate's native engine.
2. **Risk: Ollama JSON format non-compliance.**
   * *Mitigation:* Use Ollama's `format="json"` API parameter combined with strict JSON extraction regex (`_parse_script_response`) already proven in Qreate's script generator.
3. **Risk: Process hung during video rendering.**
   * *Mitigation:* Purffle runner will execute with a hard timeout (e.g., 300 seconds) and asynchronous process termination to prevent background worker deadlocks.
4. **Risk: Cloudinary upload failure in offline dev environments.**
   * *Mitigation:* Follow existing Qreate pattern: keep the local MP4 available and return the local path or task message if Cloudinary is not configured.
5. **Risk: GPU VRAM exhaustion during simultaneous LLM generation and video encoding.**
   * *Mitigation:* Sequential pipeline: script generation with Ollama finishes and unloads/idles before Purffle FFmpeg rendering starts. Purffle primarily utilizes CPU/FFmpeg encoders (`libx264`) or lightweight NVENC.

---

## 9. Next Step

**Milestone 1 is complete.** No code or package changes have been applied.  
**State exactly ONE next step:**  
Proceed to **Phase 1 & Phase 2** — Record git checkpoint and establish the isolated PurffleShorts baseline environment (Phase 4 verification with no-key demo) without touching existing Qreate code.
