FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/kite-market-data /app/services/kite-market-data

ENV PYTHONPATH=/app
WORKDIR /app/services/kite-market-data
CMD ["python", "main.py"]
