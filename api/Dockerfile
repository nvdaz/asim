FROM python:3.11-slim

ENV PYTHONUNBUFFERED True

WORKDIR /app

COPY . .

ENV PORT 8080

RUN python -m pip install --no-cache-dir .

RUN mkdir cache

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}

EXPOSE ${PORT}
