FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_logging /app/app_logging
COPY services/refdata /app/services/refdata

ENV PYTHONPATH=/app
WORKDIR /app/services/refdata
CMD ["python", "main.py"]
