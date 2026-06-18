# syntax=docker/dockerfile:1

FROM node:20-slim AS template-builder
WORKDIR /build/email-playground
COPY email-playground/package.json email-playground/package-lock.json ./
RUN npm ci
COPY email-playground/ ./
RUN npm run build:templates

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=template-builder /build/src/emails/templates/ src/emails/templates/

RUN useradd --no-create-home --shell /bin/false app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
