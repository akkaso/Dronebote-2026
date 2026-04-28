FROM python:3.11-slim

WORKDIR /app

COPY requirements-pi.txt /app/requirements-pi.txt
RUN pip install --no-cache-dir websockets pytest

COPY pi/ /app/pi/

CMD ["python3", "pi/pi_ws_server.py", "--host", "0.0.0.0", "--port", "8765", "--mock"]
