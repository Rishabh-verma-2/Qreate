# Local AI Video Director Setup Guide

This guide explains how to set up, configure, and run **Qreate** as an **AI Video Director platform** powered by a local/custom LLM (**Qwen3**) and a local open-source video generation model (**Wan2.1**).

---

## 1. Architecture Overview

```
User Prompt (Frontend Studio /ai-director)
     │
     ▼
POST /api/videos/plan  OR  POST /api/videos/generate (engine="wan")
     │
     ▼
Qwen3 LLM (Local vLLM / OpenAI-compatible API)
     │
     ▼
Structured VideoPlan JSON
  ├── Title, style, duration, aspect ratio (16:9, 9:16, 1:1)
  ├── Character consistency profiles (appearance, clothing, style)
  └── Multi-scene breakdown (visual prompt, motion prompt, camera moves, narration)
     │
     ▼
Character Consistency Service (Cached reference images)
     │
     ▼
Wan2.1 Video Engine (Per-scene clip generation)
  ├── Primary: ComfyUI REST API (/prompt, /history)
  ├── Secondary: Direct Wan CLI subprocess
  └── Fallback: Native motion graphics engine (for GPU-less development)
     │
     ▼
Voiceover & Narration (Edge-TTS — free, multi-lingual, high fidelity)
     │
     ▼
FFmpeg Composition (Scene concat + transitions + audio sync + loudnorm)
     │
     ▼
Cloudinary Video Hosting & Playback
```

---

## 2. Hardware & VRAM Requirements

| Tier | LLM | Video Model | Mode | Minimum VRAM | Recommended GPU |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Development** | Qwen3-8B (AWQ) | Wan2.1-T2V-1.3B | T2V | **8–12 GB** | RTX 3080 / 4070 (12GB) |
| **Standard** | Qwen3-8B (FP16) | Wan2.1-T2V-1.3B | T2V | **16 GB** | RTX 4080 / 3090 (24GB) |
| **Production** | Qwen3-8B (AWQ) | Wan2.1-I2V-14B-480P | I2V | **24–32 GB** | RTX 3090 / 4090 / A5000 |
| **Ultra Studio** | Qwen3-8B | Wan2.1-I2V-14B-720P | I2V | **40+ GB** | A100 / H100 / RTX 6000 Ada |
| **No-GPU Fallback** | Cloud LLM (Groq/Gemini) | Native Engine | Procedural | **0 GB** | Any CPU |

> **Memory Tip:** Qwen3 and Wan2.1 do **not** need to run concurrently during generation. Qwen3 plans the screenplay in ~3 seconds, then Wan2.1 executes the scenes sequentially.

---

## 3. Step 1: Start Local Qwen3 with vLLM

Qreate connects to Qwen3 via any OpenAI-compatible API endpoint. We recommend **vLLM** for maximum throughput and low latency.

### Install vLLM
```bash
pip install vllm
```

### Run Qwen3-8B
```bash
# Standard 8B model (Requires ~16 GB VRAM)
vllm serve Qwen/Qwen3-8B \
  --port 8000 \
  --api-key EMPTY \
  --max-model-len 8192 \
  --trust-remote-code

# Quantized AWQ model (Requires ~8 GB VRAM)
vllm serve Qwen/Qwen3-8B-AWQ \
  --port 8000 \
  --api-key EMPTY \
  --quantization awq \
  --max-model-len 8192
```

### Alternatively: LM Studio (Windows / macOS)
If you prefer LM Studio:
1. Download model: `qwen2.5-7b-instruct`
2. Start local server (port 1234):
   ```bash
   lms load qwen2.5-7b-instruct --context-length 8192 --parallel 1 -y
   ```
3. Set environment variables in `backend/.env`:
   ```env
   QWEN_BASE_URL=http://localhost:1234/v1
   QWEN_MODEL=qwen2.5-7b-instruct
   QWEN_API_KEY=lm-studio
   ```

---

## 4. Step 2: Install & Configure ComfyUI (Wan2.1)

ComfyUI is the primary generation backend for Wan2.1.

### 1. Install ComfyUI
```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

### 2. Install Wan2.1 Nodes
Install the `ComfyUI-WanVideoWrapper` custom node:
```bash
cd custom_nodes
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git
cd ComfyUI-WanVideoWrapper
pip install -r requirements.txt
cd ../..
```

### 3. Download Model Weights
Place models in your `ComfyUI/models/` folder:
- **T2V 1.3B**: Download `Wan2.1-T2V-1.3B` to `ComfyUI/models/diffusion_models/`
- **I2V 14B**: Download `Wan2.1-I2V-14B-480P` or `720P` to `ComfyUI/models/diffusion_models/`
- **T5 Text Encoder**: Download `umt5_xxl_fp8_e4m3fn.safetensors` to `ComfyUI/models/text_encoders/`
- **VAE**: Download `wan_2.1_vae.safetensors` to `ComfyUI/models/vae/`

### 4. Start ComfyUI Server
```bash
python main.py --listen 127.0.0.1 --port 8188
```

---

## 5. Step 3: Direct CLI Fallback (Optional)

If you prefer to run Wan2.1 directly without ComfyUI, clone the official Wan2.1 repository:
```bash
git clone https://github.com/Wan-Video/Wan2.1.git
cd Wan2.1
pip install -r requirements.txt
```
Set `WAN_MODEL_PATH=/path/to/Wan2.1-T2V-1.3B` in `backend/.env`. Qreate will automatically invoke the CLI if ComfyUI is not reachable.

---

## 6. Step 4: Configure Backend Environment

In `backend/.env`, set the following configuration values:

```bash
# ── Local Qwen3 LLM ──────────────────────────────────────────────────────────
QWEN_BASE_URL=http://localhost:8000/v1
QWEN_MODEL=Qwen/Qwen3-8B
QWEN_API_KEY=EMPTY
QWEN_TIMEOUT_SECONDS=120
QWEN_MAX_TOKENS=4096

# ── Video Engine (wan | native) ──────────────────────────────────────────────
VIDEO_ENGINE=wan
WAN_MODE=t2v                # t2v (scene-based) or i2v (character consistent)
WAN_MODEL_SIZE=1.3B         # 1.3B | 480P | 720P
WAN_MODEL_PATH=             # Path to Wan weights if using CLI fallback

# ── ComfyUI Backend ─────────────────────────────────────────────────────────
COMFYUI_BASE_URL=http://localhost:8188
COMFYUI_TIMEOUT_SECONDS=600

# ── Cloudinary & Storage ────────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# ── MongoDB Database & Queue ────────────────────────────────────────────────
MONGODB_URI=mongodb+srv://...
EMBEDDED_WORKER=true
```

---

## 7. Step 5: Start the Qreate Application

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
On startup, Qreate runs **system diagnostics** and logs GPU VRAM, Qwen3 ping, and ComfyUI connectivity.

### Start Frontend
```bash
cd frontend
npm run dev
```

---

## 8. Verifying Your Setup

### 1. Check Diagnostics Endpoint
Visit: `http://localhost:8000/api/videos/diagnostics`

Expected response:
```json
{
  "gpu": {
    "available": true,
    "cuda": true,
    "gpu_name": "NVIDIA GeForce RTX 4090",
    "vram_gb": 24.0,
    "warning": null
  },
  "qwen": {
    "available": true,
    "base_url": "http://localhost:8000/v1",
    "model": "Qwen/Qwen3-8B",
    "models": ["Qwen/Qwen3-8B"]
  },
  "comfyui": {
    "available": true,
    "base_url": "http://localhost:8188"
  },
  "video_engine_ready": true,
  "llm_ready": true
}
```

### 2. Using the AI Director Studio in the UI
1. Navigate to `http://localhost:5173/ai-director` in your browser.
2. Enter your video concept in natural language (e.g., *"A lone astronaut discovering an ancient alien temple on Mars"*).
3. Click **"1. Plan Storyboard"**:
   - Qwen3 generates a full scene breakdown, narration script, camera directions, and character consistency descriptions.
   - Review each scene card in the storyboard grid.
4. Click **"2. Generate Video"**:
   - The embedded worker pool claims the job.
   - Generates character reference images.
   - Renders each scene sequentially via Wan2.1.
   - Generates voiceover narration with Edge-TTS.
   - Stitches all scene clips and audio together with FFmpeg.
   - Uploads to Cloudinary and displays the completed player.
5. Direct specific scenes: Click **"Regenerate"** on any scene card to provide natural language director notes to re-shoot that specific scene!

---

## 9. Troubleshooting & FAQ

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **503 Qwen AI Director error** | vLLM is not running or port is wrong | Check `vllm serve` terminal and verify `QWEN_BASE_URL`. Falls back automatically to Groq/Gemini if configured in `LLM_PROVIDER_ORDER`. |
| **CUDA Out of Memory (OOM)** | Model weights exceed GPU VRAM | Switch to `WAN_MODEL_SIZE=1.3B` and `WAN_MODE=t2v`, or use AWQ quantized model. |
| **ComfyUI connection refused** | ComfyUI not started | Start ComfyUI on port 8188: `python main.py --port 8188`. Qreate falls back to CLI mode if `WAN_MODEL_PATH` is set. |
| **Video generation runs without GPU** | No GPU detected | Qreate automatically falls back to `NativeVideoEngine` (Pillow motion graphics + FFmpeg) so development and testing can proceed without a GPU. |
| **Edge-TTS audio fails** | Network timeout | Edge-TTS retries automatically up to 3 times before using silence fallback. |
