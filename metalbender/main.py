from fastapi import FastAPI

import metalbender.config as config

app = FastAPI()


@app.get('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=config.get_fastapi_host(),
        port=config.get_fastapi_port()
    )
