FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kite /app/kite
COPY services/kite-portfolio /app/services/kite-portfolio

ENV PYTHONPATH=/app
WORKDIR /app/services/kite-portfolio
CMD ["python", "runner.py"]
