FROM python:3.11-slim

# CadQuery's CAD kernel (OCP/OpenCASCADE) dynamically links against a small
# set of system X11/GL libraries even for headless STEP/STL export.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libx11-6 \
    libexpat1 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Render (and most PaaS hosts) inject $PORT at runtime; default it for local
# `docker run` testing.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
