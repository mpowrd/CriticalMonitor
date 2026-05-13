FROM python:3.11-slim

WORKDIR /app

COPY src/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/api/ .
COPY modelo.keras .
COPY UmbralDeAnomalias.txt .

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]