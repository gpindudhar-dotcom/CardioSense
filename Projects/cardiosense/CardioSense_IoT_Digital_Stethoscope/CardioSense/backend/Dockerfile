FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /app/data/recordings
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV DATABASE_URL=sqlite:///./data/cardiosense.db
ENV RECORDINGS_DIR=/app/data/recordings
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
