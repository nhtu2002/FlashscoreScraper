FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.13 python3.13-venv python3.13-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

# Cài thư viện và tải đúng nhân Chromium khớp với phiên bản Playwright mới nhất
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . fastapi uvicorn \
    && playwright install chromium

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}"]
