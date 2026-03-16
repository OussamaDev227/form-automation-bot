FROM python:3.12-slim

# System deps for Playwright
RUN apt-get update && apt-get install -y \
    curl wget gnupg libnss3 libxss1 libasound2 \
    libatk-bridge2.0-0 libgtk-3-0 libgbm1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 10000

# PORT is injected by Render (10000); falls back to 8000 for local Docker
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
