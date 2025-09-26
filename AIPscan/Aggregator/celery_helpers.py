import logging
from functools import wraps

from AIPscan import db
from AIPscan.models import package_tasks

logger = logging.getLogger(__name__)


def write_celery_update(package_lists_task, workflow_coordinator):
    # Write status update to celery model.
    package_task = package_tasks(
        package_task_id=package_lists_task.id,
        workflow_coordinator_id=workflow_coordinator.request.id,
    )
    db.session.add(package_task)
    db.session.commit()


def with_db_session(func):
    """Ensure the scoped session is cleaned up around each call."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Unhandled exception in %s", func_name)
            try:
                db.session.rollback()
                logger.debug("Rolled back session after error in %s", func_name)
            except Exception:
                logger.exception(
                    "Failed to rollback session after error in %s", func_name
                )
            raise
        finally:
            try:
                db.session.remove()
            except Exception:
                logger.exception(
                    "Failed to dispose session after call to %s", func_name
                )

    return wrapper
