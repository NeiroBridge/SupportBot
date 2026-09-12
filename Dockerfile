FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "main.py"]
