# One small image for every service: the link, Hospital A, Hospital B and the stub KME.
# Which one runs is decided by the command in docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements-node.txt .
RUN pip install -r requirements-node.txt

COPY quantum ./quantum
COPY backend ./backend
COPY nodes ./nodes
COPY frontend/portal ./frontend/portal

# Run as an unprivileged user. /data holds the encrypted database and, if no master key is
# injected, a generated master key: mount a volume there.
RUN useradd --system --uid 10001 --no-create-home app && mkdir /data && chown app /data
USER app
ENV QKD_DATA_DIR=/data PORT=8000
VOLUME /data

HEALTHCHECK --interval=10s --timeout=4s --start-period=15s --retries=5 \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/health' % os.environ['PORT'], timeout=3)"

# Overridden per service in docker-compose.yml.
CMD ["python", "-m", "uvicorn", "nodes.channel:app", "--host", "0.0.0.0", "--port", "8000"]
