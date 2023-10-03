import asyncio
import datetime as dt

from fastapi import Depends, FastAPI
from google.cloud import compute
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import metalbender.config as config
from metalbender.data_access import SessionType, get_session, models

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
    deadline_time: dt.datetime
    deadline_time = dt.datetime.utcnow() + dt.timedelta(seconds=request.deadline_seconds)

    # Check if the GceInstance exists.
    instance = (
        db_session.query(models.GceInstance)
        .filter(
            models.GceInstance.project_id == request.instance_project_id,
            models.GceInstance.zone == request.instance_zone,
            models.GceInstance.name == request.instance_name,
        )
        .first()
    )
    if instance is None:
        instance = models.GceInstance(
            project_id=request.instance_project_id,
            zone=request.instance_zone,
            name=request.instance_name,
        )
        db_session.add(instance)
        db_session.flush()

    heartbeat = models.Heartbeat(
        instance_id=instance.id,
        added=dt.datetime.utcnow(),
        deadline=deadline_time,
    )

    db_session.add(heartbeat)
    db_session.commit()

    comp_client = compute.InstancesClient()

    # Check if the instance is running.
    instance = await run_in_threadpool(
        comp_client.get,
        project=request.instance_project_id,
        zone=request.instance_zone,
        instance=request.instance_name,
    )

    if instance.status != 'RUNNING':
        await run_in_threadpool(
            comp_client.start,
            project=request.instance_project_id,
            zone=request.instance_zone,
            instance=request.instance_name,
        )

    return {'status': 'ok'}


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
