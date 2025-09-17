from AIPscan import db
from AIPscan.models import package_tasks


def write_celery_update(package_lists_task, workflow_coordinator):
    # Write status update to celery model.
    package_task = package_tasks(
        package_task_id=package_lists_task.id,
        workflow_coordinator_id=workflow_coordinator.request.id,
    )
    db.session.add(package_task)
    db.session.commit()
