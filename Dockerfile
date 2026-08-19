FROM python:3.10-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

CMD ["python", "main.py"]
