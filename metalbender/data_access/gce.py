from metalbender.data_access import SessionType
from metalbender.data_access.models import GceInstance


def find_gce_instance(
    db_session: SessionType,
    instance_project_id: str,
    instance_zone: str,
    instance_name: str,
) -> GceInstance:
    return (
        db_session.query(GceInstance)
        .filter(
            GceInstance.project_id == instance_project_id,
            GceInstance.zone == instance_zone,
            GceInstance.name == instance_name,
        )
        .first()
    )


def create_gce_instance(
    db_session: SessionType,
    instance_project_id: str,
    instance_zone: str,
    instance_name: str,
) -> GceInstance:
    instance = GceInstance(
        project_id=instance_project_id,
        zone=instance_zone,
        name=instance_name,
    )
    db_session.add(instance)
    db_session.flush()

    return instance


def find_or_create_gce_instance(
    db_session: SessionType,
    instance_project_id: str,
    instance_zone: str,
    instance_name: str,
) -> GceInstance:
    instance = find_gce_instance(
        db_session=db_session,
        instance_project_id=instance_project_id,
        instance_zone=instance_zone,
        instance_name=instance_name,
    )

    # If the instance is missing, create it.
    if instance is None:
        instance = create_gce_instance(
            db_session=db_session,
            instance_project_id=instance_project_id,
            instance_zone=instance_zone,
            instance_name=instance_name,
        )

    return instance
