import datetime as dt

from metalbender.data_access import SessionType
from metalbender.data_access.models import Heartbeat


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
