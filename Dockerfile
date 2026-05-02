FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY pyproject.toml /workspace/
COPY docs/README.md /workspace/docs/README.md
COPY backend /workspace/backend
COPY scripts /workspace/scripts
COPY tests /workspace/tests

RUN python -m pip install --upgrade pip && \
    python -m pip install -e ".[dev]"

COPY .env.example /workspace/.env.example

RUN mkdir -p /workspace/data/raw /workspace/data/normalized /workspace/data/evidence /workspace/data/output && \
    chmod -R 777 /workspace/data

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
