FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_logging /app/app_logging
COPY kite /app/kite
COPY services/stocks /app/services/stocks

ENV PYTHONPATH=/app
WORKDIR /app/services/stocks
CMD ["python", "runner.py"]
