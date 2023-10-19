# Metalbender

Metalbender is a tool for brinding some rudimentary on-demand provisioning of computational resources.

## Installation

### Prerequisites

To run the project, you first need to copy the file `.env.template` to `.env` and fill in the relevant information. Every entry with the `_SECRETS_MANAGER_NAME` suffix are fetched from GCP Secret Manager and should not be changed unless adapted for another project.

**NB**: Make sure to replace the FASTAPI_USERNAME and FASTAPI_PASSWORD for production.

You also need to be logged in with your GCP account through the `gcloud` CLI tool. Download and install it following these instructions [here](https://cloud.google.com/sdk/docs/install), then log in by running `gcloud auth login` in your shell. You should also set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to point to your service account JSON file.

### Docker

The project can be run with Docker.

To build the project, run:
```
docker build -t metalbender:latest .
```

To run the project, you need a service account key. If you have a default service account in GOOGLE_APPLICATION_CREDENTIALS, you can run:

```bash
docker run \
  --env-file .env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/creds.json \
  -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/keys/creds.json:ro" \
  -p 8080:8080 \
  metalbender:latest
```

(NB: I've noted some issues with git bash and docker volumes. Seems like there's some unfavorable difference in how GB+Docker handles Windows path or something...)

Otherwise, set the volumne to the path of your service account key as an absolute path.

### Local

To run the project locally, you first need to install your dependencies.

[Install Poetry](http://python-poetry.org/docs/) using your preferred method, then run:

```
poetry install
```

To run the project, run:

```bash
poetry run uvicorn metalbender.main:app --reload

python -m poetry run uvicorn metalbender.main:app --host 0.0.0.0 --port 8080 --reload
```

## Usage

### API

Once the API is running, you can find OpenAPI documentation at `http://localhost:8080/docs`.

To send a request, you first need to create a base64 encoded password that matches what you set in `.env`'s `FASTAPI_PASSWORD` envvar. E.g: `echo -n bender:admin | base64`.

Then, you can send a request to the API:

```bash
URL="127.0.0.1"
PORT=8080
PASSWORD=$(echo -n admin:admin | base64)

curl \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Basic $PASSWORD" \
  -d '{"instance_project_id": "acit4040-2023", "instance_zone": "europe-west4-a", "instance_name": "test", "deadline_seconds": 60}' \
  http://$URL:$PORT/keep-alive

curl \
  -X POST \
  -H 'Content-Length: 0' \
  -H "Authorization: Basic $PASSWORD" \
  http://$URL:$PORT/stop

curl \
  -X POST \
  -H 'Content-Length: 0' \
  -H "Authorization: Basic $PASSWORD" \
  http://$URL:$PORT/clean/heartbeats

curl \
  -H "Authorization: Basic $PASSWORD" \
  http://$URL:$PORT/health
```