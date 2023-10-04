from google.cloud import compute


def start_gce_instance(
    comp_client: compute.InstancesClient,
    instance_project_id: str,
    instance_zone: str,
    instance_name: str,
) -> None:
    # Check if the instance is running.
    instance = comp_client.get(
        project=instance_project_id,
        zone=instance_zone,
        instance=instance_name,
    )

    if instance.status != 'RUNNING':
        comp_client.start(
            project=instance_project_id,
            zone=instance_zone,
            instance=instance_name,
        )
