FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_logging /app/app_logging
COPY services/prices /app/services/prices

ENV PYTHONPATH=/app
WORKDIR /app/services/prices
CMD ["python", "main.py"]
