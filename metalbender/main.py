import asyncio
import datetime as dt

from fastapi import Depends, FastAPI, status
from fastapi.responses import Response
from google.api_core import exceptions as gcp_exceptions
from google.cloud import compute
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import metalbender.config as config
from metalbender.data_access import SessionType, get_session, models
from metalbender.data_access.gce import find_or_create_gce_instance
from metalbender.data_access.heartbeat import (calculate_deadline_time,
                                               create_heartbeat)
from metalbender.gce_tools import start_gce_instance

app = FastAPI()


@app.get('/health')
async def health():
    return {'status': 'ok'}


class KeepAliveRequest(BaseModel):
    instance_project_id: str
    instance_zone: str
    instance_name: str

    deadline_seconds: int


@app.post('/keep-alive')
async def keep_alive(
    request: KeepAliveRequest,
    db_session: SessionType = Depends(get_session),
):
    try:
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

        response = Response(status_code=status.HTTP_200_OK)
    except gcp_exceptions.Forbidden:
        db_session.rollback()
        message = {'status': 'error', 'message': "You don't have permission to access this GCP resource."}
        response = Response(status_code=status.HTTP_403_FORBIDDEN, content=message)
    except Exception:
        db_session.rollback()
        message = {'status': 'error', 'message': "Unspecified error."}
        response = Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=message)

    return response


@app.post('/stop')
async def stop_instance(db_session: SessionType = Depends(get_session)):
    project = config.get_gcp_project_id()
    comp_client = compute.InstancesClient()
    agg_list = await run_in_threadpool(comp_client.aggregated_list, project=project)
    instance_lists = [
        x[1].instances
        for x in agg_list
        if x[1].warning.code != 'NO_RESULTS_ON_PAGE'
    ]
    instances = [x for y in instance_lists for x in y if x.status == 'RUNNING']

    # Check if the instance has a heartbeat.
    current_time_utc = dt.datetime.utcnow()

    def get_valid_heartbeats() -> list[models.Heartbeat]:
        return (
            db_session.query(models.Heartbeat)
            .join(models.GceInstance, onclause=models.Heartbeat.instance_id == models.GceInstance.id)
            .filter(models.Heartbeat.deadline > current_time_utc)
            .all()
        )
    heartbeats = await run_in_threadpool(get_valid_heartbeats)

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

    async def stop_instance(instance):
        await run_in_threadpool(
            comp_client.stop,
            project=project,
            zone=instance.zone.split('/')[-1],
            instance=instance.name,
        )

    futures = [stop_instance(instance) for instance in instances]
    await asyncio.gather(*futures)

    return {'status': 'ok'}


@app.post('/clean/heartbeats')
async def clean_heartbeats(db_session: SessionType = Depends(get_session)):
    async def remove_heartbeats():
        db_session.query(models.Heartbeat).filter(models.Heartbeat.deadline < dt.datetime.utcnow()).delete()
        db_session.commit()

    await run_in_threadpool(remove_heartbeats)

    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=config.get_fastapi_host(),
        port=config.get_fastapi_port(),
    )
