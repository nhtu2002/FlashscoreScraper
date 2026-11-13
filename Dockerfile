FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir . fastapi uvicorn

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}"]
