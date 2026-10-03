# CLAUDE.md — Qreate (team NeoQuant, CTRL FREAK 2026 · Qoneqt AI Challenge)

## Context
- Qoneqt = community-first social app (Reddit + short video). We are building for its **Global Feed**.
- Problem statement: an **LLM-powered pipeline** that turns a topic / prompt / idea / trend into an
  engaging, **publish-ready vertical video**. Must be **repeatable and work at scale**, not a one-off.
  Flow: Input → LLM (hook + script + scene plan) → visuals → voice + captions → composed video → publish.
- Judges score what is **actually built, deployed and shipped**. Deliverables: public GitHub repo,
  **live deployed link**, 3–4 min demo video.
- Hard constraints from the team: **free / open-source tools only** (no paid APIs), videos must look
  **professional and not AI-generated**, must handle load.
- Git: work on branch `kartik-updates`. **Never push to `main`.** Teammate's original work is on `main`.
- Communication style the user wants: short, point-wise, simple language.

## Architecture (v2)
```
frontend (React+Vite, Vercel)  →  FastAPI (Docker on Render/HF Spaces)
                                     │  POST /api/pipeline/run | /api/batches | /api/videos/generate
                                     ▼
                              MongoDB `video_tasks` = job queue (lease-based claim)
                                     ▼
                     Worker pool (embedded in API, or `python -m app.worker` ×N)
   script (LLM chain) → voice (Edge-TTS, word timings) → real footage (Pexels/Pixabay/Openverse)
   → FFmpeg: 1080x1920 scenes, Ken Burns for stills, grade, xfade → ASS captions → music ducking
   → loudnorm −14 LUFS → Cloudinary upload → generated_videos (+ post caption & hashtags)
```

### Key files (backend/app)
- `services/script/generator.py` — TWO passes: writer (picks format STORY/MYTH-BUST/LIST/HOW-TO/POV/
  COMPARISON/PERSONAL, drafts 3 hooks, writes for the ear) → editor (retention rules, removes AI clichés).
  Emojis/symbols stripped from spoken text. Hindi = Devanagari, Hinglish = Roman script.
- `services/llm/client.py` — OpenAI-compatible provider chain: groq → openrouter → gemini → agnes → ollama.
  Invalid JSON / over-long script → error fed back to the LLM for one retry, then next provider.
- `services/script/generator.py` — system prompt (3-second hook rules, filmable `search_queries`,
  word budget ≤ 2.5 × seconds), validator, `script_fields_for_db`.
- `services/media/stock.py` — footage search order + relevance filter for keyless sources; per-job
  `StockContext` prevents reusing a clip. `TTLCache` saves free-tier API quota.
- `services/media/tts.py` — whole script spoken in ONE take (per-scene clips sounded robotic); scene cuts
  derived from word timestamps. Voice per (language, gender); rate/pitch per tone. Hinglish → en-IN Neerja/Prabhat.
- `api/routes/uploads.py` + `fetch_user_media` — creator's own photos/clips replace stock for every scene.
- `services/media/captions.py` — ASS word-highlight captions (Poppins ExtraBold, bundled in `assets/fonts`, OFL).
- `services/media/composer.py` — all FFmpeg work (async subprocesses, never blocks the event loop).
- `services/pipeline/runner.py` — `produce_video()` orchestrates stages and reports progress.
- `worker/queue.py` (claim/renew/fail_exhausted), `worker/runner.py` (WorkerPool, process_job).
- `api/routes/pipeline.py` — one-shot run, batches, queue stats. `videos.py` — queue render for an edited script.

### Frontend (frontend/src)
- `pages/BatchStudio.tsx` — many topics → many videos, live per-video progress (`/batch`, `/batch/:id`).
- `components/VideoCard.tsx` — 9:16 player, download (Cloudinary `fl_attachment`), copy caption+hashtags.
- Create → Script Editor → Generate flow still exists for single, hand-edited videos.

## Running locally
```bash
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # fill MONGODB_URI, CLOUDINARY_*, GROQ_API_KEY, PEXELS_API_KEY
uvicorn app.main:app --reload --port 8000          # API + embedded worker
python -m app.worker                                # optional extra workers (scale out)
cd ../frontend && npm install && npm run dev        # VITE_API_BASE_URL=http://localhost:8000
```
FFmpeg: uses system `ffmpeg` if present, else the `imageio-ffmpeg` bundled binary (has libass).

## Deployment
- Backend: `backend/Dockerfile` (python 3.11 + ffmpeg + fonts). `render.yaml` blueprint at repo root.
  Render free = 0.1 CPU → slow renders; Hugging Face Spaces (Docker, free 2 vCPU/16 GB, set PORT=7860)
  is a stronger free option. Set env vars from `.env.example`.
- Frontend: Vercel, root `frontend`, env `VITE_API_BASE_URL=<backend url>`; `vercel.json` has SPA rewrites.
- CORS: `FRONTEND_URL` + `EXTRA_CORS_ORIGINS`; `*.vercel.app` allowed by `CORS_ORIGIN_REGEX`.

## Decisions & gotchas
- No AI-generated imagery or AI video: real footage is what keeps output from looking AI-made.
  The old Agnes video engine + `free_generator.py` were removed (still on `main` / git history).
- Without `PEXELS_API_KEY`, visuals come only from Openverse StockSnap/Nappy (strict match); everything
  else becomes a bold TEXT CARD over a blurred neighbouring shot. The wider Openverse archive
  (Wikimedia, Rawpixel, museums) was removed — it returned vases/owls/old scans for modern topics.
  Pexels paused new API keys (Oct 2026) → use **Pixabay** (videos+photos) and **Unsplash** (photos); both free/instant.
- Pixabay: only `type == film` clips; tags matching green screen/animation/3D/text are rejected; match ≥ 0.5.
  Place words (Mumbai, India…) are mandatory in matches (`PLACES` in stock.py).
- CLIP visual matching (`services/media/vision.py`): pools candidates from all sources, scores thumbnails
  vs the scene's visual_description, best wins; < RERANK_MIN_SCORE → text card. Optional dep (requirements-ml.txt).
- Voice chain in composer (EQ + compression) makes TTS sit like a recorded VO. Next step if still
  "too AI": Kokoro-82M (open-source TTS, needs Python ≥3.10 + ~1 GB RAM) as optional engine.
- CC-BY photo credits are stored on each video (`credits`) — show them in the post if used.
- Old `backend/.env` with real secrets was committed on `main` → keys must be rotated; `.env` now ignored.
- Scaling knobs: `WORKER_CONCURRENCY`, `SCENE_RENDER_PARALLELISM`, `MAX_QUEUE_DEPTH` (429 back-pressure),
  `MAX_BATCH_SIZE`, `EMBEDDED_WORKER=false` + separate worker processes.
- Qoneqt has no known public posting API → "publish" = download MP4 + copy generated caption/hashtags.

## Status / TODO
- [x] 9:16 1080x1920 output · [x] 3-second hook prompt · [x] batch mode · [x] Docker/Render/Vercel config
- [ ] Get free keys: Groq, Pexels (+ Pixabay) → set on Render
- [ ] Rotate leaked Mongo/Cloudinary/Agnes secrets
- [ ] Deploy backend + frontend, record 3–4 min demo
