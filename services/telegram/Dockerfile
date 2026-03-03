FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_logging /app/app_logging
COPY messaging /app/messaging
COPY services/telegram /app/services/telegram

ENV PYTHONPATH=/app
WORKDIR /app/services/telegram
CMD ["python", "main.py"]
