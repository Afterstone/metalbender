FROM python:3.11-slim-bookworm

WORKDIR /app

RUN adduser --disabled-login nopriv \
    && chown -R nopriv:nopriv /app/
USER nopriv

RUN pip install --no-cache-dir poetry==1.6.1
RUN python -m poetry config virtualenvs.in-project true
COPY pyproject.toml poetry.lock ./
RUN python -m poetry install --no-interaction

COPY . .

ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8000

CMD [\
    "/bin/sh", "-c", \
    "python -m poetry run uvicorn metalbender.main:app --host $FASTAPI_HOST --port $FASTAPI_PORT" \
]