FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-pc.txt /app/requirements-pc.txt
RUN pip install --no-cache-dir -r requirements-pc.txt

COPY pc/ /app/pc/

CMD ["python3", "-m", "pc.vision_client", "--no-display", "--mock"]
