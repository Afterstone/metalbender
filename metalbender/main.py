import asyncio
import datetime as dt
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.api_core import exceptions as gcp_exceptions
from google.cloud import compute
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import metalbender.config as config
from metalbender.data_access import SessionType, get_session
from metalbender.data_access.gce import find_or_create_gce_instance
from metalbender.data_access.heartbeat import (calculate_deadline_time,
                                               create_heartbeat,
                                               get_valid_heartbeats,
                                               remove_heartbeats)
from metalbender.gce_tools import (get_running_gce_instances,
                                   start_gce_instance, stop_gce_instance)

app = FastAPI()
security = HTTPBasic()


class RequestError(Exception):
    pass


class Status(str, Enum):
    ok = "ok"
    error = "error"
    warning = "warning"


class ApiResponse(BaseModel):
    status: Status
    message: str


class BasicUser(BaseModel):
    username: str
    password: str


def get_user_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> BasicUser:
    correct_username = config.get_fastapi_username()
    correct_password = config.get_fastapi_password()
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return BasicUser(username=credentials.username, password=credentials.password)


@app.get('/health')
async def health(
    _: str = Depends(get_user_credentials),
):
    return Response(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(status=Status.ok, message="Healthy").model_dump_json(),
    )


class KeepAliveRequest(BaseModel):
    instance_project_id: str
    instance_zone: str
    instance_name: str

    deadline_seconds: int


@app.post('/keep-alive')
async def keep_alive(
    request: KeepAliveRequest,
    db_session: SessionType = Depends(get_session),
    _: str = Depends(get_user_credentials),
):
    response: Response
    api_response: ApiResponse
    try:
        if request.deadline_seconds < 10:
            raise RequestError("Deadline must be at least 10 seconds to ensure start/stop doesn't overlap.")

        db_session.begin()

        # Check if the GceInstance exists.
        instance = await run_in_threadpool(
            find_or_create_gce_instance,
            db_session=db_session,
            instance_project_id=request.instance_project_id,
            instance_zone=request.instance_zone,
            instance_name=request.instance_name,
        )

        deadline_time = calculate_deadline_time(
            start_time=dt.datetime.utcnow(),
            seconds_to_deadline=request.deadline_seconds,
        )
        await run_in_threadpool(
            create_heartbeat,
            db_session=db_session,
            instance_id=instance.id,  # type: ignore
            deadline_time=deadline_time,
        )

        comp_client = compute.InstancesClient()

        await run_in_threadpool(
            start_gce_instance,
            comp_client=comp_client,
            instance_project_id=request.instance_project_id,
            instance_zone=request.instance_zone,
            instance_name=request.instance_name,
        )

        api_response = ApiResponse(status=Status.ok, message="Keep-alive request added.")
        response = Response(status_code=status.HTTP_200_OK, content=api_response.model_dump_json())
    except gcp_exceptions.Forbidden:
        db_session.rollback()
        api_response = ApiResponse(status=Status.error, message="You don't have permission to access this GCP resource.")
        response = Response(status_code=status.HTTP_403_FORBIDDEN, content=api_response.model_dump_json())
    except RequestError as e:
        db_session.rollback()
        api_response = ApiResponse(status=Status.error, message=str(e))
        response = Response(status_code=status.HTTP_400_BAD_REQUEST, content=api_response.model_dump_json())
    except Exception:
        db_session.rollback()
        api_response = ApiResponse(status=Status.error, message="Unspecified error.")
        response = Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=api_response.model_dump_json())

    return response


@app.post('/stop')
async def stop_instance(
    db_session: SessionType = Depends(get_session),
    _: str = Depends(get_user_credentials),
):
    response: Response
    api_response: ApiResponse
    try:
        db_session.begin()

        project = config.get_gcp_project_id()
        comp_client = compute.InstancesClient()

        instances = await run_in_threadpool(get_running_gce_instances, comp_client=comp_client, project=project)
        heartbeats = await run_in_threadpool(get_valid_heartbeats, db_session=db_session, current_time_utc=dt.datetime.utcnow())

        # Remove instances that have a valid heartbeat.
        instances = [
            x for x in instances
            if not any(
                y.gce_instance.name == x.name
                and y.gce_instance.zone == x.zone.split('/')[-1]
                and y.gce_instance.project_id == project
                for y in heartbeats
            )
        ]

        # Stop all running instances without a valid heartbeat.
        futures = [
            run_in_threadpool(
                stop_gce_instance,
                project=project,
                instance=instance,
                zone=instance.zone.split('/')[-1],
            )
            for instance in instances
        ]
        await asyncio.gather(*futures)

        api_response = ApiResponse(status=Status.ok, message=f"{len(instances)} instances stopped.")
        response = Response(status_code=status.HTTP_200_OK, content=api_response.model_dump_json())
    except Exception:
        db_session.rollback()
        api_response = ApiResponse(status=Status.error, message="Unspecified error.")
        response = Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=api_response.model_dump_json())

    return response


@app.post('/clean/heartbeats')
async def clean_heartbeats(
    db_session: SessionType = Depends(get_session),
    _: str = Depends(get_user_credentials),
) -> Response:
    response: Response
    api_response: ApiResponse

    try:
        db_session.begin()
        await run_in_threadpool(remove_heartbeats, db_session=db_session)

        api_response = ApiResponse(status=Status.ok, message="Heartbeats cleaned.")
        response = Response(status_code=status.HTTP_200_OK, content=api_response.model_dump_json())
    except Exception:
        db_session.rollback()
        # message = {'status': 'error', 'message': "Unspecified error."}
        api_response = ApiResponse(status=Status.error, message="Unspecified error.")
        response = Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=api_response)

    return response

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=config.get_fastapi_host(),
        port=config.get_fastapi_port(),
    )
