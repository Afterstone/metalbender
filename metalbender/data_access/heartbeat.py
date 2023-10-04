import datetime as dt

from metalbender.data_access import SessionType
from metalbender.data_access.models import GceInstance, Heartbeat


def calculate_deadline_time(start_time: dt.datetime, seconds_to_deadline: int) -> dt.datetime:
    return start_time + dt.timedelta(seconds=seconds_to_deadline)


def create_heartbeat(
    db_session: SessionType,
    instance_id: int,
    deadline_time: dt.datetime,
) -> Heartbeat:
    heartbeat = Heartbeat(
        instance_id=instance_id,
        added=dt.datetime.utcnow(),
        deadline=deadline_time,
    )
    db_session.add(heartbeat)
    db_session.flush()

    return heartbeat


def remove_heartbeats(db_session: SessionType):
    db_session.query(Heartbeat).filter(Heartbeat.deadline < dt.datetime.utcnow()).delete()
    db_session.commit()


def get_valid_heartbeats(
    db_session: SessionType,
    current_time_utc: dt.datetime,
) -> list[Heartbeat]:
    return (
        db_session.query(Heartbeat)
        .join(GceInstance, onclause=Heartbeat.instance_id == GceInstance.id)
        .filter(Heartbeat.deadline > current_time_utc)
        .all()
    )
