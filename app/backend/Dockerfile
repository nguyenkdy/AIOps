FROM python:3.12-slim

# stress-ng de tao tai CPU/RAM tu ben trong pod
RUN apt-get update \
    && apt-get install -y --no-install-recommends stress-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
