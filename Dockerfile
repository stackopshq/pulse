FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances d'abord (cache Docker).
COPY pyproject.toml README.md ./
COPY pulse ./pulse
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["pulse", "serve", "--host", "0.0.0.0", "--port", "8000"]
