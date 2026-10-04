# Qreate API + render worker. Works on Render, Hugging Face Spaces, Fly, Railway, any Docker host.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# FFmpeg (with libass for captions) + fontconfig so libass can resolve the bundled fonts
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fontconfig fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt
# CLIP visual matching (~1 GB). Build with --build-arg WITH_ML=false for tiny hosts (e.g. 512 MB RAM).
ARG WITH_ML=true
RUN if [ "$WITH_ML" = "true" ]; then \
      pip install torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install -r requirements-ml.txt ; \
    fi

COPY app ./app
# Register the bundled open-source caption fonts system-wide as well
RUN mkdir -p /usr/share/fonts/truetype/qreate \
    && cp app/assets/fonts/*.ttf /usr/share/fonts/truetype/qreate/ \
    && fc-cache -f

# Non-root user (required by Hugging Face Spaces, good practice elsewhere)
RUN useradd -m -u 1000 appuser
USER appuser
# Pre-download the CLIP weights into the image so the first job is fast
RUN if [ "$WITH_ML" = "true" ]; then \
      python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')" ; \
    fi

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
