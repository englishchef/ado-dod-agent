FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=container

WORKDIR /workspace

COPY pyproject.toml /workspace/
COPY docs/README.md /workspace/docs/README.md
COPY langgraph.json /workspace/langgraph.json
COPY backend /workspace/backend
COPY scripts /workspace/scripts
COPY .env.example /workspace/.env.example

RUN python -m pip install --upgrade pip && \
    python -m pip install .

RUN useradd --create-home --shell /usr/sbin/nologin appuser && \
    mkdir -p /workspace/data && \
    chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
