# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

RUN groupadd --system medagent \
    && useradd --system --gid medagent --create-home medagent

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock

COPY src/ ./src/
COPY --from=frontend-builder /build/frontend/dist/ ./frontend/dist/

RUN mkdir -p /app/data/index/chroma /app/data/index/medrag \
    && chown -R medagent:medagent /app

USER medagent

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
