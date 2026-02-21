FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
COPY web /app/web
COPY migrations /app/migrations
COPY README.md /app/README.md
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
