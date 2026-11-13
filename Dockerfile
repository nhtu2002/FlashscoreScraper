FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Cài đặt Python 3.13 từ kho deadsnakes PPA trên Ubuntu 24.04 (Noble)
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.13 python3.13-venv python3.13-dev \
    && rm -rf /var/lib/apt/lists/*

# Tạo môi trường ảo riêng dùng Python 3.13
RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

# Cài đặt thư viện của dự án vào Python 3.13
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . fastapi uvicorn

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}"]
