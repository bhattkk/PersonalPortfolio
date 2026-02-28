FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/stocks-refdata /app/services/stocks-refdata

ENV PYTHONPATH=/app
WORKDIR /app/services/stocks-refdata
CMD ["python", "main.py"]
