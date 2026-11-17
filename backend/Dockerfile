ARG PYTHON_IMAGE=python:3.12.16-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt && useradd --uid 10001 --create-home crm
COPY backend/ .
USER 10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
