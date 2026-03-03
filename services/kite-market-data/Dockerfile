FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_logging /app/app_logging
COPY services/kite-market-data /app/services/kite-market-data

ENV PYTHONPATH=/app
WORKDIR /app/services/kite-market-data
CMD ["python", "main.py"]
