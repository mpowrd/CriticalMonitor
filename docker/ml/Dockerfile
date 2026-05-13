FROM python:3.11-slim

WORKDIR /app

COPY src/distributed/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/distributed/ .

CMD ["python", "coordinator.py"]