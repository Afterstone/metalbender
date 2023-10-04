FROM python:3.11-alpine3.18

# Set the working directory
WORKDIR /app

# Add a non-privileged user and set the ownership of the working directories
RUN adduser -D nopriv \
    && chown -R nopriv:nopriv /app/
USER nopriv

# Install and configure poetry
RUN pip install --no-cache-dir poetry==1.6.1
RUN python -m poetry config virtualenvs.in-project true

# Copy the project files into the image
COPY pyproject.toml poetry.lock ./

# Install the project dependencies
RUN python -m poetry install --no-interaction

# Copy the rest of the project files into the image
COPY . .

# Set environment variables for FastAPI
ENV FASTAPI_HOST=0.0.0.0
ENV FASTAPI_PORT=8080

# Set the command to run when the image starts
CMD [\
    "/bin/sh", "-c", \
    "python -m poetry run uvicorn metalbender.main:app --host $FASTAPI_HOST --port $FASTAPI_PORT" \
]
