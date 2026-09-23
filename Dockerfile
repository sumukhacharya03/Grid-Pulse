# Grid-Pulse, ready to host: the dashboard in public demo mode (no Kafka).
#   docker build -t grid-pulse .
#   docker run -p 8080:8080 -v gridpulse-data:/data grid-pulse
# The SQLite file (game + the season's live weekends) lives in /data, so
# mount a volume there to keep everyone's portfolios across redeploys.

FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRIDPULSE_MODE=demo \
    GRIDPULSE_PUBLIC=1 \
    GRIDPULSE_DB=/data/gridpulse.db \
    HOST=0.0.0.0 \
    PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gridpulse/ gridpulse/
COPY dashboard.py .
COPY assets/ assets/
COPY baseline_market_value/drivers_baseline_value.csv baseline_market_value/
COPY generator/historical/generated_historical_results/ generator/historical/generated_historical_results/
COPY generator/real_data/results_2025/ generator/real_data/results_2025/
COPY --from=web /web/dist web/dist

RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=4)"
CMD ["python", "dashboard.py"]
