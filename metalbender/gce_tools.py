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


def get_running_gce_instances(
    comp_client: compute.InstancesClient,
    project: str,
) -> list[compute.Instance]:
    agg_list = comp_client.aggregated_list(project=project)
    instance_lists = [
        x[1].instances
        for x in agg_list
        if x[1].warning.code != 'NO_RESULTS_ON_PAGE'
    ]
    instances = [x for y in instance_lists for x in y if x.status == 'RUNNING']
    return instances


def stop_gce_instance(
    project: str,
    instance: compute.Instance,
    zone: str,
) -> None:
    comp_client = compute.InstancesClient()
    comp_client.stop(
        project=project,
        zone=zone.split('/')[-1],
        instance=instance.name,
    )
